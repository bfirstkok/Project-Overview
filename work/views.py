import calendar
import csv
import io
import json
from datetime import date, timedelta
from pathlib import Path
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Avg
from django.db.models.deletion import ProtectedError
from django.http import FileResponse, HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from .models import User, Project, Task, Status, Comment, Attachment, Activity, Team
from .forms import ProjectForm, TaskForm, CommentForm, AttachmentForm, CreateUserForm, EditUserForm, TeamForm
from .permissions import projects_for, tasks_for, edit_project, edit_task, manage_task, activities_for, assignable_users
from .filters import filter_tasks, HEADERS
from .services import save_work, inline_update, delete_work, EditConflict, update_grid, InvalidGridEdit

def audit(user, summary, obj=None):
    return Activity.objects.create(actor=user, summary=summary, task=obj if isinstance(obj, Task) else None, project=obj if isinstance(obj, Project) else None)

def page(request, qs, size=20): return Paginator(qs, size).get_page(request.GET.get('page'))

def filtered_tasks(request):
    return filter_tasks(request)[0]


def filter_context(user):
    visible_users = User.objects.filter(Q(pk=user.pk) | Q(tasks__in=tasks_for(user)) | Q(sales_tasks__in=tasks_for(user)) | Q(engineering_tasks__in=tasks_for(user)), is_service_account=False, is_active=True).distinct()
    return {'projects': projects_for(user), 'people': visible_users, 'sales_people': visible_users.filter(role__in=['sales','intern']), 'engineer_people': visible_users.filter(role__in=['engineer','intern']), 'statuses': Status.choices, 'priorities': Task.Priority.choices}

def stats(qs):
    return qs.aggregate(total=Count('id', distinct=True), done=Count('id', filter=Q(status=Status.DONE), distinct=True), pending=Count('id', filter=~Q(status__in=[Status.DONE, Status.CANCELLED]), distinct=True), progress=Count('id', filter=Q(status=Status.PROGRESS), distinct=True), overdue=Count('id', filter=Q(due_date__lt=timezone.localdate()) & ~Q(status__in=[Status.DONE, Status.CANCELLED]), distinct=True), high=Count('id', filter=Q(priority__in=['high', 'critical']) & ~Q(status__in=[Status.DONE, Status.CANCELLED]), distinct=True))

@login_required
def dashboard(request):
    tasks = tasks_for(request.user)
    summary = stats(tasks)
    workload = []
    metric_people = assignable_users(request.user) if request.user.is_manager else User.objects.filter(Q(tasks__in=tasks) | Q(sales_tasks__in=tasks) | Q(engineering_tasks__in=tasks)).distinct()
    for person in metric_people:
        person_tasks = tasks.filter(Q(sales=person) | Q(engineer=person) | Q(assignees=person)).distinct()
        workload.append({'person':person,'stats':stats(person_tasks)})
    sales_rows = [{'person':r['person'],'stats':stats(tasks.filter(sales=r['person']))} for r in workload if r['person'].eligible_for('sales')]
    engineer_rows = [{'person':r['person'],'stats':stats(tasks.filter(Q(engineer=r['person']) | Q(assignees=r['person'])).distinct())} for r in workload if r['person'].eligible_for('engineer')]
    chart = [{'label': label, 'value': tasks.filter(status=value).count(), 'key': value} for value, label in Status.choices]
    return render(request, 'work/dashboard.html', {'workload':workload,'sales_rows':sales_rows,'engineer_rows':engineer_rows,'summary': summary, 'project_count': projects_for(request.user).count(), 'my_tasks': tasks.filter(Q(sales=request.user) | Q(engineer=request.user) | Q(assignees=request.user)).distinct().exclude(status__in=[Status.DONE, Status.CANCELLED])[:5], 'due_tasks': tasks.filter(due_date__isnull=False).exclude(status__in=[Status.DONE, Status.CANCELLED]).order_by('due_date')[:6], 'activities': activities_for(request.user)[:6], 'chart': chart, 'chart_json': chart, 'today': timezone.localdate()})

@login_required
def project_list(request):
    qs = projects_for(request.user)
    if request.GET.get('q'): qs = qs.filter(Q(title__icontains=request.GET['q']) | Q(customer__icontains=request.GET['q']))
    if request.GET.get('status'): qs = qs.filter(status=request.GET['status'])
    return render(request, 'work/projects.html', {'page': page(request, qs, 12), 'statuses': Status.choices})

@login_required
def project_detail(request, pk):
    project = get_object_or_404(projects_for(request.user), pk=pk)
    return render(request, 'work/project_detail.html', {'project': project, 'tasks': tasks_for(request.user).filter(project=project), 'can_edit': edit_project(request.user, project), 'attachment_form': AttachmentForm(), 'activities': activities_for(request.user).filter(project=project)[:30]})


@login_required
def project_form(request, pk=None):
    return work_form(request, pk, 'project')

def work_form(request, pk, kind):
    is_task = kind == 'task'
    obj = get_object_or_404(tasks_for(request.user) if is_task else projects_for(request.user), pk=pk) if pk else None
    if obj and not (edit_task(request.user, obj) if is_task else edit_project(request.user, obj)): raise PermissionDenied
    initial = {}
    if is_task and request.GET.get('project', '').isdigit(): initial['project'] = get_object_or_404(projects_for(request.user), pk=request.GET['project'])
    if not is_task and not obj: initial['owner'] = request.user
    form_type = TaskForm if is_task else ProjectForm
    form = form_type(request.POST if request.method == 'POST' else None, instance=obj, user=request.user, initial=initial)
    status = 200
    if request.method == 'POST':
        try:
            form, saved = save_work(request.user, request.POST, pk, kind)
            if saved:
                messages.success(request, 'บันทึกข้อมูลแล้ว')
                return redirect(f'{kind}_detail', pk=saved.pk)
        except EditConflict as exc:
            form.is_valid()
            form.add_error(None, str(exc))
            status = 409
        except (Task.DoesNotExist, Project.DoesNotExist): raise Http404
    return render(request, 'work/form.html', {'form': form, 'title': ('อัปเดตงาน' if obj else 'สร้างงานใหม่') if is_task else ('แก้ไขโปรเจกต์' if obj else 'สร้างโปรเจกต์'), 'subtitle':'Status และ % Complete แยกกัน กรุณาตรวจสอบทั้งสองช่องก่อนบันทึก', 'conflict':status == 409}, status=status)

@login_required
def task_list(request):
    qs, filter_form = filter_tasks(request)
    ctx = filter_context(request.user)
    mode = request.GET.get('view', 'list')
    if mode == 'kanban':
        ctx['columns'] = [{'label': label, 'key': value, 'tasks': qs.filter(status=value)} for value, label in Status.choices]
    elif mode == 'calendar':
        from .calendar_view import calendar_context
        ctx.update(calendar_context(request, qs))
    else: mode = 'list'
    page_size = {'20':20,'50':50,'100':100}.get(request.GET.get('per_page','20'),20)
    task_page = page(request, qs, page_size)
    for task in task_page:
        task.can_manage = request.user.is_manager or task.creator_id == request.user.pk
        task.can_edit = task.can_manage or request.user.pk in [task.sales_id, task.engineer_id] or any(p.pk == request.user.pk for p in task.assignees.all())
    sort = request.GET.get('sort') or '-no'
    from .filters import SORTS
    if sort.lstrip('-') not in SORTS: sort = '-no'
    headers = [{'key':key, 'label':label, 'next':('-'+key if sort == key else key), 'active':sort.lstrip('-') == key, 'descending':sort.startswith('-')} for key,label in HEADERS]
    ctx.update(page_size=page_size, task_summary=stats(qs), page=task_page, view=mode, filter_form=filter_form, headers=headers, all_sales=assignable_users(request.user).filter(role__in=['sales','intern']), all_engineers=assignable_users(request.user).filter(role__in=['engineer','intern']))
    return render(request, 'work/tasks.html', ctx)

@login_required
def task_detail(request, pk):
    task = get_object_or_404(tasks_for(request.user), pk=pk)
    return render(request, 'work/task_detail.html', {'task': task, 'can_edit': edit_task(request.user, task), 'can_manage': manage_task(request.user, task), 'comment_form': CommentForm(), 'attachment_form': AttachmentForm(), 'activities': task.activity_set.select_related('actor')[:50]})

@login_required
def task_form(request, pk=None):
    return work_form(request, pk, 'task')

@login_required
@require_POST
def task_grid(request):
    try:
        if len(request.body) > 1024 * 1024: raise InvalidGridEdit('ข้อมูลใหญ่เกินไป')
        data = json.loads(request.body)
        if not isinstance(data, dict): raise ValueError()
        return JsonResponse({'saved': update_grid(request.user, data.get('rows'))})
    except EditConflict as exc: return JsonResponse({'error':str(exc)}, status=409)
    except InvalidGridEdit as exc: return JsonResponse({'error':str(exc)}, status=422)
    except (ValueError, TypeError, KeyError, AttributeError):
        return JsonResponse({'error':'รูปแบบข้อมูลไม่ถูกต้อง'}, status=400)
    except Task.DoesNotExist: raise Http404

@login_required
@require_POST
def task_inline(request, pk):
    get_object_or_404(tasks_for(request.user), pk=pk)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict): raise ValueError()
        form, obj = inline_update(request.user, pk, data.get('field'), data.get('value'), data.get('version'))
        if not obj: return JsonResponse({'errors':form.errors}, status=422)
        return JsonResponse({'version':obj.version, 'status':obj.status, 'progress':obj.progress})
    except EditConflict as exc: return JsonResponse({'error':str(exc)}, status=409)
    except (ValueError, TypeError): return JsonResponse({'error':'ข้อมูลไม่ถูกต้อง'}, status=400)
    except Task.DoesNotExist: raise Http404

@login_required
@require_POST
def add_comment(request, pk):
    task = get_object_or_404(tasks_for(request.user), pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            comment = form.save(commit=False); comment.task = task; comment.author = request.user; comment.save()
            audit(request.user, f'แสดงความคิดเห็น: {comment.body}', task)
        messages.success(request, 'เพิ่มความคิดเห็นแล้ว')
    else: messages.error(request, 'กรุณาระบุความคิดเห็นไม่เกิน 5,000 ตัวอักษร')
    return redirect('task_detail', pk=pk)

@login_required
@require_POST
def upload(request, kind, pk):
    obj = get_object_or_404(tasks_for(request.user) if kind == 'task' else projects_for(request.user), pk=pk)
    if not (edit_task(request.user, obj) if kind == 'task' else edit_project(request.user, obj)): raise PermissionDenied
    form = AttachmentForm(request.POST, request.FILES)
    if form.is_valid():
        item = form.save(commit=False); setattr(item, kind, obj); item.author = request.user
        item.original_name = Path(request.FILES['file'].name).name[:255]; item.save()
        audit(request.user, f'แนบไฟล์ {item.original_name}', obj)
        messages.success(request, 'อัปโหลดไฟล์แล้ว')
    else: messages.error(request, 'ไฟล์ไม่ถูกต้อง: ' + form.errors.as_text())
    return redirect(f'{kind}_detail', pk=pk)

@login_required
def download(request, pk):
    item = get_object_or_404(Attachment, pk=pk)
    if item.task_id: get_object_or_404(tasks_for(request.user), pk=item.task_id)
    else: get_object_or_404(projects_for(request.user), pk=item.project_id)
    try: response = FileResponse(item.file.open('rb'), as_attachment=True, filename=item.original_name, content_type='application/octet-stream')
    except FileNotFoundError: return HttpResponse('ไม่พบไฟล์ กรุณาติดต่อผู้ดูแลระบบ', status=404)
    response['X-Content-Type-Options'] = 'nosniff'
    return response

@login_required
def delete_object(request, kind, pk):
    obj = get_object_or_404(tasks_for(request.user) if kind == 'task' else projects_for(request.user), pk=pk)
    if not (manage_task(request.user, obj) if kind == 'task' else edit_project(request.user, obj)): raise PermissionDenied
    if request.method == 'POST':
        try:
            delete_work(request.user, pk, kind, request.POST.get('version'))
        except EditConflict as exc:
            obj.refresh_from_db()
            return render(request,'work/delete.html',{'object':obj,'conflict':str(exc)},status=409)
        except (Task.DoesNotExist, Project.DoesNotExist): raise Http404
        except ProtectedError:
            messages.error(request, 'ลบโปรเจกต์ไม่ได้เพราะยังมีงานอยู่ กรุณาย้ายหรือลบงานก่อน')
            return redirect('project_detail', pk=pk)
        messages.success(request, 'ลบรายการแล้ว')
        return redirect('tasks' if kind == 'task' else 'projects')
    return render(request, 'work/delete.html', {'object': obj})

@login_required
def team_view(request):
    if not request.user.is_manager: raise PermissionDenied
    people = []
    for person in assignable_users(request.user).select_related('team'):
        qs = tasks_for(request.user).filter(Q(sales=person) | Q(engineer=person) | Q(assignees=person)).distinct()
        people.append({'person': person, 'stats': stats(qs), 'average': round(qs.aggregate(v=Avg('progress'))['v'] or 0), 'tasks': qs.exclude(status__in=[Status.DONE, Status.CANCELLED])[:5]})
    return render(request, 'work/team.html', {'people': people, 'staff_groups': [{'label':label,'rows':[row for row in people if row['person'].role==role]} for role,label in [('sales','Sales'),('engineer','Engineer'),('intern','Intern · ช่วยงานได้ทั้งสองทีม')]]})

@login_required
def activity_view(request): return render(request, 'work/activity.html', {'page': page(request, activities_for(request.user), 30)})

@login_required
def reports(request):
    qs = filtered_tasks(request)
    if request.GET.get('export') in ['csv', 'xlsx']: return export_report(qs, request.GET['export'])
    ctx = filter_context(request.user)
    ctx['filter_form'] = filter_tasks(request)[1]
    people = User.objects.filter(Q(tasks__in=qs) | Q(sales_tasks__in=qs) | Q(engineering_tasks__in=qs)).distinct()
    ctx.update(summary=stats(qs), page=page(request, qs), person_rows=[{'name': str(p), 'stats': stats(qs.filter(Q(sales=p) | Q(engineer=p) | Q(assignees=p)).distinct())} for p in people], project_rows=[{'name': str(p), 'stats': stats(qs.filter(project=p))} for p in projects_for(request.user).filter(tasks__in=qs).distinct()])
    return render(request, 'work/reports.html', ctx)

def safe_cell(value):
    value = str(value or '')
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value

def export_report(qs, mode):
    from .excel import workbook_template
    rows=[]
    for task in qs:
        person_name = lambda person: str(person) if task.source_data else person.username
        engineers = ([person_name(task.engineer)] if task.engineer else []) + [person_name(person) for person in task.assignees.all() if person.pk != task.sales_id]
        rows.append([task.register_number, str(task.project or ''), task.title, task.get_priority_display(), task.get_status_display(), task.start_date, task.due_date, task.progress, person_name(task.sales) if task.sales else '', ', '.join(engineers), task.notes_to_colleague])
    if mode=='csv':
        from .excel import COLUMNS
        response=HttpResponse(content_type='text/csv; charset=utf-8-sig'); response.write('\ufeff')
        writer=csv.writer(response); writer.writerow([label for key,label in COLUMNS])
        for row in rows: writer.writerow([safe_cell(value) if isinstance(value,str) else value for value in row])
    else:
        book=workbook_template(); sheet=book['Tasks']
        for row in rows:
            sheet.append(row)
            for cell in sheet[sheet.max_row]:
                if isinstance(cell.value,str): cell.data_type='s'
            for col in ['F','G']: sheet[f'{col}{sheet.max_row}'].number_format='yyyy-mm-dd'
        sheet.auto_filter.ref=f'A1:K{max(1,sheet.max_row)}'
        output=io.BytesIO(); book.save(output)
        response=HttpResponse(output.getvalue(),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition']=f'attachment; filename="tasks-{timezone.localdate()}.{mode}"'
    return response

@login_required
def users(request):
    if not request.user.is_admin: raise PermissionDenied
    return render(request, 'work/users.html', {'people': User.objects.filter(is_service_account=False).select_related('team').order_by('role','first_name','pk')})

@login_required
def user_form(request, pk=None):
    if not request.user.is_admin: raise PermissionDenied
    obj = get_object_or_404(User, pk=pk) if pk else None
    form = (EditUserForm if obj else CreateUserForm)(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        if obj and obj.pk == request.user.pk and (not form.cleaned_data['is_active'] or (form.cleaned_data['role'] != obj.Role.ADMIN and not obj.has_admin_access and not obj.is_superuser)):
            form.add_error(None, 'ไม่สามารถปิดใช้งานหรือลดสิทธิ์ Admin ของตนเองได้')
        elif obj and obj.is_superuser and not request.user.is_superuser:
            raise PermissionDenied
        else:
            person = form.save()
            audit(request.user, f'{"แก้ไข" if obj else "สร้าง"}ผู้ใช้ {person.username} | {person.role} | active={person.is_active}')
            messages.success(request, 'บันทึกผู้ใช้แล้ว'); return redirect('users')
    return render(request, 'work/form.html', {'form': form, 'title': 'แก้ไขผู้ใช้' if obj else 'เพิ่มผู้ใช้', 'subtitle': 'สิทธิ์และทีมสำหรับการทำงานร่วมกัน'})

@login_required
def reset_password(request, pk):
    from .sso import local_login_allowed
    if not request.user.is_admin or not local_login_allowed(): raise PermissionDenied
    person = get_object_or_404(User, pk=pk)
    if person.is_superuser and not request.user.is_superuser: raise PermissionDenied
    form = SetPasswordForm(person, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save(); audit(request.user, f'ตั้งรหัสผ่านใหม่ให้ {person.username}')
        messages.success(request, 'ตั้งรหัสผ่านใหม่แล้ว'); return redirect('users')
    return render(request, 'work/form.html', {'form': form, 'title': f'ตั้งรหัสผ่าน: {person.username}'})

@login_required
def team_create(request):
    if not request.user.is_admin: raise PermissionDenied
    form = TeamForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        team = form.save(); audit(request.user, f'สร้างทีม {team.name}'); return redirect('users')
    return render(request, 'work/form.html', {'form': form, 'title': 'เพิ่มทีม'})
