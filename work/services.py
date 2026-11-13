from django.core.exceptions import PermissionDenied
from django.db import transaction
from .models import Task, Project, Activity
from .forms import TaskForm, ProjectForm
from .permissions import edit_task, edit_project

TASK_FIELDS = ['title', 'project', 'description', 'sales', 'engineer', 'sales_members', 'engineer_members', 'priority', 'status', 'start_date', 'due_date', 'progress', 'notes_to_colleague', 'work_notes']
PROJECT_FIELDS = ['title', 'customer', 'category', 'description', 'owner', 'status', 'start_date', 'due_date', 'document_url']

class EditConflict(Exception):
    pass

class InvalidGridEdit(Exception):
    pass

@transaction.atomic
def update_grid(user, rows):
    """Save a pasted range as one transaction, including audit records."""
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise InvalidGridEdit('รองรับครั้งละ 1–100 งาน')
    seen = set()
    saved = []
    for row in sorted(rows, key=lambda item: int(item['id'])):
        pk = int(row['id'])
        if pk in seen: raise InvalidGridEdit('มีงานซ้ำในรายการ')
        seen.add(pk)
        obj = Task.objects.select_for_update().get(pk=pk)
        if not edit_task(user, obj): raise PermissionDenied
        changes = row.get('changes')
        form = TaskForm(instance=obj, user=user)
        if not isinstance(changes, dict) or not 1 <= len(changes) <= 10:
            raise InvalidGridEdit('ไม่มีข้อมูลแก้ไข หรือจำนวนคอลัมน์ไม่ถูกต้อง')
        for field in changes:
            if field not in TASK_FIELDS or field not in form.fields or form.fields[field].disabled:
                raise PermissionDenied
        data = task_data(obj)
        for role in ['sales','engineer']:
            if role in changes and role+'_members' not in changes: data.pop(role+'_members',None)
        data.update(changes)
        data['version'] = row.get('version')
        validated, item = save_work(user, data, pk=pk)
        if item is None:
            errors = ' · '.join(str(error) for group in validated.errors.values() for error in group)
            raise InvalidGridEdit(f'งาน #{pk}: {errors}')
        saved.append({'id': item.pk, 'version': item.version})
    return saved

def snapshot(obj, fields, relation):
    data = {field: (', '.join(str(person) for person in getattr(obj,field).all()) if hasattr(getattr(obj,field),'all') else str(getattr(obj, field) if getattr(obj, field) is not None else '')) for field in fields}
    data[relation] = ', '.join(str(u) for u in getattr(obj, relation).all())
    return data

@transaction.atomic
def save_work(user, data, pk=None, kind='task'):
    model, form_type = (Task, TaskForm) if kind == 'task' else (Project, ProjectForm)
    relation = 'assignees' if kind == 'task' else 'members'
    fields = TASK_FIELDS if kind == 'task' else PROJECT_FIELDS
    obj = model.objects.select_for_update().get(pk=pk) if pk else None
    if obj:
        if not (edit_task(user, obj) if kind == 'task' else edit_project(user, obj)): raise PermissionDenied
        try: submitted_version = int(data.get('version', ''))
        except (ValueError, TypeError): submitted_version = None
        if submitted_version != obj.version: raise EditConflict('มีคนแก้ไขข้อมูลนี้แล้ว กรุณาเปิดข้อมูลล่าสุดและตรวจสอบก่อนบันทึกอีกครั้ง ข้อมูลของคุณยังไม่ถูกบันทึก')
    before = snapshot(obj, fields, relation) if obj else None
    if kind == 'task': data = normalize_task_data(data,obj)
    form = form_type(data, instance=obj, user=user)
    if not form.is_valid(): return form, None
    item = form.save(commit=False)
    if not item.pk and kind == 'task': item.creator = user
    if before is not None: item.version += 1
    item.save(); form.save_m2m()
    summary = f'สร้าง{kind} {item.title}'
    if before is not None:
        after = snapshot(item, fields, relation)
        changes = [f'{item._meta.get_field(key).verbose_name}: {before[key] or "—"} → {value or "—"}' for key, value in after.items() if before[key] != value]
        summary = f'แก้ไข {item.title} | ' + (' | '.join(changes) if changes else 'บันทึกข้อมูลเดิม')
    Activity.objects.create(actor=user, summary=summary, **{kind: item})
    return form, item

@transaction.atomic
def inline_update(user, pk, field, value, version):
    obj = Task.objects.select_for_update().get(pk=pk)
    if not edit_task(user, obj): raise PermissionDenied
    form = TaskForm(instance=obj, user=user)
    if field not in form.Meta.fields or form.fields[field].disabled: raise PermissionDenied
    data = task_data(obj)
    if field in ['sales','engineer']: data.pop(field+'_members',None)
    data['version'] = version
    data[field] = value
    return save_work(user, data, pk=pk)

def task_data(obj):
    data = {name:getattr(obj,name) for name in TaskForm.Meta.fields if name not in ['assignees','sales_members','engineer_members']}
    for name in ['project','sales','engineer']: data[name] = getattr(obj,name+'_id') or ''
    for name in ['assignees','sales_members','engineer_members']: data[name] = list(getattr(obj,name).values_list('pk',flat=True))
    for role in ['sales','engineer']:
        if not data[role+'_members'] and data[role]: data[role+'_members'] = [data[role]]
    return data

def normalize_task_data(data,obj):
    result = data.copy()
    result['_legacy_assignment_roles'] = [role for role in ['sales','engineer'] if role in data and role+'_members' not in data and role+'_members_present' not in data]
    for role in ['sales','engineer']:
        field = role+'_members'
        if field in data or field+'_present' in data:
            values = data.getlist(field) if hasattr(data,'getlist') else data.get(field,[])
            if not isinstance(values,(list,tuple)): values = [values] if values else []
        elif role in data:
            value = data.get(role)
            values = [getattr(value,'pk',value)] if value else []
        else:
            values = list(getattr(obj,field).values_list('pk',flat=True)) if obj else []
            if not values and obj and getattr(obj,role+'_id'): values = [getattr(obj,role+'_id')]
        values = [value for value in values if value not in ['',None]]
        if hasattr(result,'setlist'): result.setlist(field,values)
        else: result[field] = values
        result[role] = values[0] if values else ''
    return result

@transaction.atomic
def delete_work(user, pk, kind, version):
    from .permissions import manage_task
    model = Task if kind == 'task' else Project
    obj = model.objects.select_for_update().get(pk=pk)
    if not (manage_task(user,obj) if kind=='task' else edit_project(user,obj)): raise PermissionDenied
    try: submitted=int(version)
    except (ValueError,TypeError): submitted=None
    if submitted!=obj.version: raise EditConflict('รายการถูกแก้ไขหลังเปิดหน้ายืนยัน กรุณาตรวจข้อมูลล่าสุดก่อนลบ')
    Activity.objects.create(actor=user,summary=f'ลบ {kind} #{obj.pk}: {obj.title} | สถานะ {obj.get_status_display()} | version {obj.version}',**{kind:obj})
    obj.delete()
