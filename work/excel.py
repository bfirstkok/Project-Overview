"""Bounded XLSX reader and explicit, previewable import. Never evaluate formulas."""
import hashlib
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zipfile import ZipFile, BadZipFile
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction, connection
from django.utils import timezone
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils.datetime import from_excel, CALENDAR_MAC_1904, CALENDAR_WINDOWS_1900
from .models import Task, Project, User, Activity
from .permissions import projects_for, tasks_for, assignable_users
from .forms import TaskForm
from .filters import HEADERS

COLUMNS = [('no','No.'),('project','Project Name'),('title','Task'),('priority','Priority'),('status','Status'),('start_date','Start Date'),('due_date','End Date'),('progress','% Complete'),('sales','Sales'),('engineer','Engineer'),('notes_to_colleague','Notes to Colleague')]
MAX_ROWS = 2000

def normalize(value): return ' '.join(str(value or '').strip().casefold().split())

def read_xlsx(upload, sheet_name='', header_row=1):
    if not upload.name.lower().endswith('.xlsx') or upload.size > 5 * 1024 * 1024:
        raise ValidationError('ใช้ไฟล์ .xlsx ขนาดไม่เกิน 5 MB เท่านั้น')
    raw = upload.read()
    try:
        with ZipFile(io.BytesIO(raw)) as archive:
            if len(archive.infolist()) > 2000 or sum(item.file_size for item in archive.infolist()) > 30 * 1024 * 1024:
                raise ValidationError('ไฟล์เมื่อขยายมีขนาดเกินขีดจำกัด 30 MB')
        book = load_workbook(io.BytesIO(raw), read_only=True, data_only=False, keep_links=False)
        if sheet_name and sheet_name not in book.sheetnames: raise ValidationError('ไม่พบชื่อ Worksheet ที่ระบุ')
        sheet = book[sheet_name] if sheet_name else book.active
        if sheet.max_column and sheet.max_column > 100: raise ValidationError('รองรับไม่เกิน 100 คอลัมน์')
        if sheet.max_row and sheet.max_row - header_row > MAX_ROWS:
            raise ValidationError(f'ไฟล์มีมากกว่า {MAX_ROWS} แถวหลังหัวคอลัมน์ กรุณาแบ่งไฟล์หรือลบแถวว่างที่จัดรูปแบบไว้ เพื่อป้องกันการนำเข้าไม่ครบ')
        rows = []
        for index, row in enumerate(sheet.iter_rows(min_row=header_row, max_row=header_row+MAX_ROWS+1, max_col=min(sheet.max_column or 100,100)), start=header_row):
            values = []
            for cell in row:
                value = cell.value
                kind = 'text'
                if cell.data_type == 'f': kind = 'formula'
                elif isinstance(value, (date, datetime)): kind = 'date'; value = value.date().isoformat() if isinstance(value,datetime) else value.isoformat()
                elif isinstance(value, (int,float)): kind = 'percent' if '%' in cell.number_format else 'number'
                values.append({'value':str(value) if value is not None else '', 'kind':kind})
            if index == header_row: headers = [v['value'] for v in values]
            elif any(v['value'].strip() for v in values):
                rows.append({'row':index, 'cells':values})
                if len(rows) > MAX_ROWS: raise ValidationError(f'รองรับไม่เกิน {MAX_ROWS} แถวต่อครั้ง กรุณาแบ่งไฟล์')
        epoch = '1904' if book.epoch == CALENDAR_MAC_1904 else '1900'
        book.close()
        if not rows or not any(headers): raise ValidationError('ไม่พบหัวคอลัมน์หรือข้อมูล ตรวจสอบ Header Row และ Worksheet')
        return {'headers':headers, 'rows':rows, 'sheet':sheet.title, 'epoch':epoch}
    except ValidationError: raise
    except Exception as exc:
        raise ValidationError('อ่านไฟล์ Excel ไม่สำเร็จ กรุณาตรวจสอบว่าเป็น .xlsx ที่เปิดได้และไม่มีการเข้ารหัส') from exc

class UploadForm(forms.Form):
    file = forms.FileField(label='Excel (.xlsx ไม่เกิน 5 MB)')
    sheet_name = forms.CharField(label='Worksheet (เว้นว่างใช้ active sheet)', required=False, max_length=100)
    header_row = forms.IntegerField(label='แถวหัวคอลัมน์', initial=1, min_value=1, max_value=100)

def initial_mapping(payload):
    headers = {normalize(h):str(i) for i,h in enumerate(payload['headers'])}
    aliases = {'title':['task','งาน','ชื่องาน'], 'project':['project name','project','โปรเจกต์'], 'progress':['% complete','% complete.','progress','ความคืบหน้า %'], 'priority':['priority','ความสำคัญ'], 'status':['status','สถานะ'], 'start_date':['start date','วันเริ่มต้น'], 'due_date':['end date','due date','กำหนดเสร็จ'], 'notes_to_colleague':['notes to colleague','notes','บันทึกถึงเพื่อนร่วมงาน']}
    return {key:next((headers[a] for a in [normalize(label)] + aliases.get(key,[]) if a in headers),'') for key,label in COLUMNS}

class MappingForm(forms.Form):
    create_projects = forms.BooleanField(label='อนุญาตสร้าง Project ใหม่จากชื่อในไฟล์ (ไม่เดาข้อมูลลูกค้า)', required=False)
    new_category = forms.ChoiceField(label='ประเภทสำหรับ Project ใหม่', choices=Project.Category.choices, initial='solution')
    fill_project = forms.BooleanField(label='ใช้ Project Name จากแถวก่อนหน้าเมื่อช่องว่าง (เช่น Excel เดิมมีเซลล์รวม)',required=False)
    def __init__(self, payload, *args, **kwargs):
        super().__init__(*args,**kwargs)
        choices=[('','ไม่ใช้คอลัมน์นี้')] + [(str(i),f'{i+1}. {h or "(ไม่มีชื่อ)"}') for i,h in enumerate(payload['headers'])]
        for key,label in COLUMNS:
            self.fields['col_'+key] = forms.ChoiceField(label=label, choices=choices, required=key=='title', initial=initial_mapping(payload)[key])
    def clean(self):
        data=super().clean()
        cols=[v for k,v in data.items() if k.startswith('col_') and v != '']
        if len(cols)!=len(set(cols)): raise forms.ValidationError('แต่ละคอลัมน์ใช้ได้เพียงครั้งเดียว กรุณาตรวจสอบ Mapping')
        return data

def cell_at(row, mapping, field):
    column=mapping.get(field,'')
    if column=='': return {'value':'','kind':'text'}
    return row['cells'][int(column)]

def assignment_names(value):
    return [name.strip() for name in re.split(r'[,\n&/]+',value or '') if name.strip()]

def person_key(role, name): return 'person_'+hashlib.sha256((role+'|'+normalize(name)).encode()).hexdigest()[:16]

def find_person(people, name, role):
    matches=[p for p in people if p.eligible_for(role) and normalize(name) in [normalize(p.username),normalize(p.get_full_name())]]
    return matches[0] if len(matches)==1 else None

def person_controls(payload, mapping, user, submitted=None):
    people=list(assignable_users(user))
    result=[]; seen=set()
    for row in payload['rows']:
        for role in ['sales','engineer']:
            for name in assignment_names(cell_at(row,mapping,role)['value']):
                if name.casefold()=='all' or (role,normalize(name)) in seen: continue
                seen.add((role,normalize(name)))
                key=person_key(role,name); match=find_person(people,name,role)
                selected=(submitted.get(key,'') if submitted is not None else str(match.pk) if match else '')
                result.append({'key':key,'role':role,'name':name,'selected':selected,'people':[p for p in people if p.eligible_for(role)]})
    return result

def parse_date(cell, epoch):
    value=cell['value'].strip()
    if not value: return None
    if cell['kind']=='number':
        dt=from_excel(float(value), CALENDAR_MAC_1904 if epoch=='1904' else CALENDAR_WINDOWS_1900)
        if not isinstance(dt,datetime): raise ValueError('เลขวันที่ Excel ไม่ถูกต้อง')
        if not 1900<=dt.year<=2100: raise ValueError('วันที่ต้องอยู่ระหว่าง ค.ศ. 1900–2100')
        return dt.date()
    value=re.sub(r'พ\.?ศ\.?|ค\.?ศ\.?','',value).strip()
    parts=re.split(r'[-/]',value)
    if len(parts)!=3: raise ValueError('วันที่ต้องเป็น DD/MM/YYYY หรือ YYYY-MM-DD (รองรับ พ.ศ.)')
    if len(parts[0].strip())==4: year,month,day=map(int,parts)
    elif len(parts[2].strip())==4: day,month,year=map(int,parts)
    else: raise ValueError('ระบุปี 4 หลักเพื่อป้องกันการตีความผิด')
    if year>=2400: year-=543
    if not 1900<=year<=2100: raise ValueError('วันที่ต้องอยู่ระหว่าง ค.ศ. 1900–2100')
    return date(year,month,day)

def parse_progress(cell):
    value=cell['value'].strip().replace('%','').strip()
    if not value: return 0
    try:
        number=Decimal(value)
        if cell['kind']=='percent': number*=100
        if not number.is_finite() or number!=number.to_integral_value() or not 0<=number<=100: raise ValueError()
        return int(number)
    except (InvalidOperation,ValueError): raise ValueError('% Complete ต้องเป็นจำนวนเต็ม 0–100 หรือเซลล์รูปแบบเปอร์เซ็นต์')

def choice_value(value, field):
    aliases={'priority':{'normal':'normal','medium':'normal','ปานกลาง':'normal','ต่ำ':'low','สูง':'high','เร่งด่วนที่สุด':'critical'}, 'status':{'to do':'todo','in progress':'progress','on hold':'hold','complete':'done','completed':'done','cancelled':'cancelled','canceled':'cancelled','รอดำเนินการ':'todo','กำลังดำเนินการ':'progress','พักงาน':'hold','เสร็จแล้ว':'done','ยกเลิก':'cancelled'}}
    default='normal' if field=='priority' else 'todo'
    cleaned=normalize(value)
    if not cleaned: return default
    cleaned=aliases[field].get(cleaned,cleaned)
    valid=Task.Priority.values if field=='priority' else Task._meta.get_field('status').choices
    valid=valid if field=='priority' else [v for v,l in valid]
    if cleaned not in valid: raise ValueError(f'{field}: ค่าที่ไม่รองรับ "{value}"')
    return cleaned

def preview_rows(batch, user):
    payload, mapping, options=batch.payload,batch.mapping,batch.options
    people=list(assignable_users(user)); allowed_ids={p.pk for p in people}
    project_index={}
    for project in projects_for(user): project_index.setdefault(normalize(project.title),[]).append(project)
    visible_tasks=list(tasks_for(user))
    existing={(normalize(t.project.title) if t.project else '',normalize(t.title)) for t in visible_tasks}
    existing_ids={str(t.pk):t for t in visible_tasks}
    seen=set(); previous=''; result=[]
    for row in payload['rows']:
        errors=[]; warnings=[]; values={key:cell_at(row,mapping,key)['value'].strip() for key,label in COLUMNS}
        if options.get('fill_project'):
            if values['project']: previous=values['project']
            else: values['project']=previous
        for key,label in COLUMNS:
            if cell_at(row,mapping,key)['kind']=='formula': errors.append(f'{label}: มีสูตร กรุณาใช้ Paste Values ก่อนนำเข้า')
        data={'title':values['title'], 'notes_to_colleague':values['notes_to_colleague'], 'assignees':[]}
        project=None; new_project=False
        if not values['title']: errors.append('Task ต้องไม่ว่าง')
        if values['no']:
            try:
                no=Decimal(values['no'])
                if not no.is_finite() or no!=no.to_integral_value() or no<1: raise ValueError()
            except (InvalidOperation,ValueError): errors.append('No. ต้องเป็นจำนวนเต็มบวกหรือเว้นว่างสำหรับงานใหม่')
        if len(values['title'])>200 or len(values['project'])>200: errors.append('Project / Task ยาวเกิน 200 ตัวอักษร')
        if len(values['notes_to_colleague'])>5000: errors.append('Notes ยาวเกิน 5,000 ตัวอักษร')
        matches=project_index.get(normalize(values['project']),[])
        if values['project']:
            if len(matches)>1: errors.append('พบ Project ชื่อซ้ำ กรุณาแก้ชื่อให้ชัดเจนก่อนนำเข้า')
            elif matches: project=matches[0]
            elif options.get('create_projects'): new_project=True
            else: errors.append('ไม่พบ Project ที่เข้าถึงได้ ให้สร้าง Project ก่อนหรืออนุญาตสร้างใหม่')
        data['project']=project.pk if project else ''
        for role in ['sales','engineer']:
            selected_people=[]
            names=assignment_names(values[role])
            if any(name.casefold()=='all' for name in names):
                selected_people=[p for p in people if p.eligible_for(role)]
                warnings.append(f'{role}: ALL จับคู่ผู้มีสิทธิ์ในทีม {len(selected_people)} คน')
            else:
                for name in names:
                    selected=options.get('people',{}).get(person_key(role,name))
                    person=next((p for p in people if str(p.pk)==str(selected) and p.eligible_for(role)),None) if selected else find_person(people,name,role)
                    if not person: errors.append(f'{role}: ไม่พบผู้ใช้ที่มีสิทธิ์/ชื่อซ้ำ กรุณาจับคู่ชื่อ "{name}"')
                    elif person not in selected_people: selected_people.append(person)
            data[role]=selected_people[0].pk if selected_people else ''
            data[role+'_members']=[p.pk for p in selected_people]
            for person in selected_people:
                if project and person.pk!=project.owner_id and not project.members.filter(pk=person.pk).exists(): errors.append(f'{role}: ต้องเพิ่ม {person} เป็นสมาชิกโปรเจกต์ก่อน')
        try:
            for field in ['priority','status']: data[field]=choice_value(values[field],field)
            for field in ['start_date','due_date']:
                data[field]=parse_date(cell_at(row,mapping,field),payload['epoch'])
                raw=cell_at(row,mapping,field)['value']
                if re.search(r'\b2[45]\d{2}\b',raw): warnings.append(f'{field}: แปลง พ.ศ. เป็น {data[field]}')
            data['progress']=parse_progress(cell_at(row,mapping,'progress'))
            if data['start_date'] and data['due_date'] and data['due_date']<data['start_date']: errors.append('End Date ต้องไม่ก่อน Start Date')
        except (ValueError,OverflowError) as exc: errors.append(str(exc))
        identity=(normalize(values['project']),normalize(values['title']))
        duplicate=identity in existing or identity in seen
        # An exported No. is a hint only: never overwrite or silently attach another task.
        old=existing_ids.get(values['no'])
        if old and (normalize(old.project.title) if old.project else '',normalize(old.title))==identity: duplicate=True
        if not errors: seen.add(identity)
        if new_project and data.get('sales') and data['sales'] not in allowed_ids: errors.append('Sales ไม่อยู่ในขอบเขตสิทธิ์')
        state='error' if errors else 'duplicate' if duplicate else 'new'
        serial={k:(v.isoformat() if isinstance(v,date) else v) for k,v in data.items()}
        result.append({'row':row['row'],'state':state,'errors':errors,'warnings':warnings,'values':values,'data':serial,'new_project':new_project})
    return result

@transaction.atomic
def commit_batch(batch, user, allow_partial=False, expected_revision=None):
    from .models import ImportBatch
    from .services import save_work
    wanted_revision = batch.revision if expected_revision is None else expected_revision
    batch=ImportBatch.objects.select_for_update().get(pk=batch.pk,owner=user)
    if batch.confirmed_at: raise ValidationError('ชุดข้อมูลนี้นำเข้าแล้ว ไม่สามารถยืนยันซ้ำได้')
    if str(wanted_revision)!=str(batch.revision): raise ValidationError('Preview ถูกแก้ไขจากอีกแท็บ กรุณาตรวจ Preview ล่าสุดก่อนยืนยันอีกครั้ง')
    if (timezone.now()-batch.created_at).total_seconds()>86400: raise ValidationError('ชุดข้อมูลหมดอายุ กรุณาอัปโหลดใหม่')
    # Serialize imports so duplicate checking also holds across two simultaneous batches.
    if connection.vendor=='postgresql':
        with connection.cursor() as cursor: cursor.execute('SELECT pg_advisory_xact_lock(%s)',[71231011])
    rows=preview_rows(batch,user)
    batch.preview=rows; batch.save(update_fields=['preview'])
    if any(r['state']=='error' for r in rows) and not allow_partial: return 0,rows,False
    created_projects={}; count=0
    for row in rows:
        if row['state']!='new': continue
        data=row['data'].copy()
        if row['new_project']:
            key=normalize(row['values']['project'])
            if key not in created_projects:
                project=Project.objects.create(title=row['values']['project'],customer='',category=batch.options.get('new_category','solution'),owner=user)
                # All people are drawn from the explicit, permission-checked mapping.
                members={int(member) for r in rows if normalize(r['values']['project'])==key and r['state']=='new' for role in ['sales','engineer'] for member in r['data'].get(role+'_members',[])}
                project.members.add(*members)
                Activity.objects.create(actor=user,project=project,summary=f'สร้างโปรเจกต์จาก Excel: {project.title}')
                created_projects[key]=project
            data['project']=created_projects[key].pk
        form,task=save_work(user,data)
        if not task: raise ValidationError(f'แถว {row["row"]}: {form.errors.as_text()}')
        Activity.objects.create(actor=user,task=task,summary=f'นำเข้าจาก Excel {batch.filename} / แถว {row["row"]}')
        count+=1
    batch.confirmed_at=timezone.now(); batch.save(update_fields=['confirmed_at'])
    return count,rows,True

def workbook_template():
    book=Workbook(); sheet=book.active; sheet.title='Tasks'
    sheet.append([label for key,label in COLUMNS]); sheet.freeze_panes='D2'; sheet.auto_filter.ref='A1:K2001'
    for col,width in {'A':10,'B':36,'C':44,'D':15,'E':18,'F':17,'G':17,'H':16,'I':24,'J':24,'K':60}.items(): sheet.column_dimensions[col].width=width
    for cell in sheet[1]: cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='244D47')
    for col,values in [('D','Low,Normal,High,Critical'),('E','To Do,In Progress,On Hold,Complete,Cancelled')]:
        rule=DataValidation(type='list',formula1='"'+values+'"',allow_blank=True); rule.errorTitle='Invalid value'; rule.error='Select a value from the dropdown'; rule.showErrorMessage=True; sheet.add_data_validation(rule); rule.add(f'{col}2:{col}2001')
    rule=DataValidation(type='whole',operator='between',formula1=0,formula2=100,allow_blank=True); rule.showErrorMessage=True; sheet.add_data_validation(rule); rule.add('H2:H2001')
    help_sheet=book.create_sheet('Instructions')
    for line in ['Template only — no company data included.','Task is required. Blank Project Name means a standalone task.','Use account usernames in Sales / Engineer to avoid ambiguous full names.','Dates: Excel dates, DD/MM/YYYY or YYYY-MM-DD. Buddhist years are supported.','% Complete: integer 0–100, or an Excel percentage-formatted cell.','Status and progress are independent; neither changes automatically.','Duplicate Project + Task names are skipped; existing records are never overwritten.','No. is exported task ID; leave blank for new rows.','Blank Priority / Status / Progress default to Normal / To Do / 0.','Preview and confirm before import. Correct errors or explicitly import valid rows only.']:
        help_sheet.append([line])
    help_sheet.column_dimensions['A'].width=110
    return book
