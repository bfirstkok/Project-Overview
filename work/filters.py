from django import forms
from django.db.models import Q, Case, When, Value, IntegerField
from .models import Task, Status
from .permissions import tasks_for

class TaskFilters(forms.Form):
    no = forms.IntegerField(required=False, min_value=1)
    q = forms.CharField(required=False, max_length=200)
    project_name = forms.CharField(required=False, max_length=200)
    task_name = forms.CharField(required=False, max_length=200)
    notes = forms.CharField(required=False, max_length=5000)
    status = forms.ChoiceField(required=False, choices=[('', 'All')] + Status.choices)
    priority = forms.ChoiceField(required=False, choices=[('', 'All')] + Task.Priority.choices)
    project = forms.IntegerField(required=False, min_value=1)
    sales = forms.IntegerField(required=False, min_value=1)
    engineer = forms.IntegerField(required=False, min_value=1)
    assignees = forms.IntegerField(required=False, min_value=1)
    start_from = forms.DateField(required=False)
    start_to = forms.DateField(required=False)
    end_from = forms.DateField(required=False)
    end_to = forms.DateField(required=False)
    progress_min = forms.IntegerField(required=False, min_value=0, max_value=100)
    progress_max = forms.IntegerField(required=False, min_value=0, max_value=100)

SORTS = {'no': 'pk', 'project': 'project__title', 'task': 'title', 'priority': '_priority', 'status': '_status', 'start': 'start_date', 'end': 'due_date', 'progress': 'progress', 'sales': 'sales__username', 'engineer': 'engineer__username', 'notes': 'notes_to_colleague'}
HEADERS = [('no','No.'),('project','Project Name'),('task','Task'),('priority','Priority'),('status','Status'),('start','Start Date'),('end','End Date'),('progress','% Complete'),('sales','Sales'),('engineer','Engineer'),('notes','Notes to Colleague')]

def filter_tasks(request):
    qs = tasks_for(request.user)
    form = TaskFilters(request.GET)
    if not form.is_valid(): return qs.none(), form
    data = form.cleaned_data
    if data['q']: qs = qs.filter(Q(title__icontains=data['q']) | Q(project__title__icontains=data['q']))
    for param, field in [('no','pk'),('project','project_id'),('sales','sales_id'),('engineer','engineer_id'),('priority','priority'),('status','status'),('project_name','project__title__icontains'),('task_name','title__icontains'),('notes','notes_to_colleague__icontains'),('start_from','start_date__gte'),('start_to','start_date__lte'),('end_from','due_date__gte'),('end_to','due_date__lte'),('progress_min','progress__gte'),('progress_max','progress__lte')]:
        if data[param] is not None and data[param] != '': qs = qs.filter(**{field:data[param]})
    if data['assignees']:
        p = data['assignees']; qs = qs.filter(Q(sales_id=p) | Q(engineer_id=p) | Q(assignees__pk=p))
    if request.GET.get('mine'): qs = qs.filter(Q(sales=request.user) | Q(engineer=request.user) | Q(assignees=request.user))
    if request.GET.get('overdue'):
        from django.utils import timezone
        qs = qs.filter(due_date__lt=timezone.localdate()).exclude(status__in=[Status.DONE, Status.CANCELLED])
    if request.GET.get('high'): qs = qs.filter(priority__in=['high','critical']).exclude(status__in=[Status.DONE, Status.CANCELLED])
    qs = qs.annotate(_priority=Case(*[When(priority=p, then=Value(i)) for i,p in enumerate(['low','normal','high','critical'])],default=Value(0),output_field=IntegerField()), _status=Case(*[When(status=s,then=Value(i)) for i,s in enumerate(Status.values)],default=Value(0),output_field=IntegerField()))
    sort = request.GET.get('sort','no')
    key = SORTS.get(sort.lstrip('-'),'pk')
    return qs.order_by(('-' if sort.startswith('-') else '')+key,'pk').distinct(), form
