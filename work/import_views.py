import csv
import io
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import ImportBatch
from .excel import UploadForm, MappingForm, COLUMNS, read_xlsx, person_controls, preview_rows, commit_batch, workbook_template

def format_form(form):
    for field in form.fields.values(): field.widget.attrs['class']='form-check-input' if getattr(field.widget,'input_type','')=='checkbox' else 'form-select' if hasattr(field.widget,'choices') else 'form-control'

@login_required
def import_upload(request):
    form=UploadForm(request.POST or None, request.FILES or None)
    if request.method=='POST' and form.is_valid():
        try:
            payload=read_xlsx(form.cleaned_data['file'],form.cleaned_data['sheet_name'],form.cleaned_data['header_row'])
            batch=ImportBatch.objects.create(owner=request.user,filename=form.cleaned_data['file'].name[:255],payload=payload)
            # Only the requesting user's expired staging data is removed, never tasks.
            ImportBatch.objects.filter(owner=request.user,created_at__lt=timezone.now()-timedelta(days=7)).delete()
            return redirect('import_preview',pk=batch.pk)
        except ValidationError as exc: form.add_error(None,exc)
    format_form(form)
    return render(request,'work/import_upload.html',{'form':form})

@login_required
def import_preview(request,pk):
    batch=get_object_or_404(ImportBatch,pk=pk,owner=request.user,created_at__gte=timezone.now()-timedelta(days=1))
    status=200
    if request.method=='POST' and request.POST.get('action')=='confirm':
        if not batch.mapping or not batch.preview:
            messages.error(request,'กรุณา Preview ก่อนยืนยัน')
        else:
            try:
                count,rows,done=commit_batch(batch,request.user,request.POST.get('allow_partial')=='on',expected_revision=request.POST.get('revision',''))
                if done:
                    messages.success(request,f'นำเข้า {count} งานเรียบร้อยแล้ว ข้อมูลซ้ำถูกข้ามและไม่มีการเขียนทับข้อมูลเดิม')
                    return redirect('tasks')
                messages.error(request,'ยังมีแถวที่ไม่ถูกต้อง กรุณาแก้ไฟล์หรือเลือกนำเข้าเฉพาะแถวที่ผ่านตรวจสอบ')
                status=422
            except ValidationError as exc:
                messages.error(request,'; '.join(exc.messages)); status=422
        batch.refresh_from_db()
    initial={**{'col_'+k:v for k,v in batch.mapping.items()},**{k:v for k,v in batch.options.items() if k!='people'}}
    mapping_form=MappingForm(batch.payload,request.POST if request.method=='POST' and request.POST.get('action')=='preview' else None,initial=initial)
    if request.method=='POST' and request.POST.get('action')=='preview' and mapping_form.is_valid() and not batch.confirmed_at:
        with transaction.atomic():
            batch=ImportBatch.objects.select_for_update().get(pk=batch.pk,owner=request.user)
            if batch.confirmed_at or request.POST.get('revision','')!=str(batch.revision):
                messages.error(request,'ชุด Preview ถูกแก้ไขหรือยืนยันจากอีกแท็บ กรุณาโหลดข้อมูลล่าสุด');status=409
            else:
                batch.mapping={key:mapping_form.cleaned_data['col_'+key] for key,label in COLUMNS}
                controls=person_controls(batch.payload,batch.mapping,request.user,request.POST)
                batch.options={key:mapping_form.cleaned_data[key] for key in ['create_projects','new_category','fill_project']}
                batch.options['people']={control['key']:control['selected'] for control in controls}
                batch.preview=preview_rows(batch,request.user)
                batch.revision+=1
                batch.save(update_fields=['mapping','options','preview','revision'])
    from .excel import initial_mapping
    mapping=batch.mapping or initial_mapping(batch.payload)
    controls=person_controls(batch.payload,mapping,request.user,batch.options.get('people') or None)
    format_form(mapping_form)
    return render(request,'work/import_preview.html',{'batch':batch,'mapping_form':mapping_form,'person_controls':controls,'rows':batch.preview,'new_count':sum(r['state']=='new' for r in batch.preview),'duplicate_count':sum(r['state']=='duplicate' for r in batch.preview),'error_count':sum(r['state']=='error' for r in batch.preview)},status=status)

@login_required
def import_errors(request,pk):
    batch=get_object_or_404(ImportBatch,pk=pk,owner=request.user)
    from .views import safe_cell
    response=HttpResponse(content_type='text/csv; charset=utf-8-sig'); response.write('\ufeff')
    writer=csv.writer(response)
    writer.writerow(['Source Row']+[label for key,label in COLUMNS]+['Errors'])
    for row in batch.preview:
        if row['state']=='error': writer.writerow([row['row']]+[safe_cell(row['values'][key]) for key,label in COLUMNS]+[safe_cell('; '.join(row['errors']))])
    response['Content-Disposition']='attachment; filename="import-errors.csv"'
    return response

@login_required
def excel_template(request):
    book=workbook_template(); output=io.BytesIO(); book.save(output)
    response=HttpResponse(output.getvalue(),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition']='attachment; filename="projectwork-import-template.xlsx"'
    return response
