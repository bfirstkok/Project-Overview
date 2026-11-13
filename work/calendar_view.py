"""Calendar presentation for already permission-filtered task querysets."""
import calendar
from datetime import date, timedelta
from django.utils import timezone

WEEKDAYS = [('จันทร์','จ.'),('อังคาร','อ.'),('พุธ','พ.'),('พฤหัสบดี','พฤ.'),('ศุกร์','ศ.'),('เสาร์','ส.'),('อาทิตย์','อา.')]

def calendar_context(request, qs):
    today = timezone.localdate()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        if not 1900 <= year <= 2100: raise ValueError()
        first = date(year, month, 1)
    except (ValueError, TypeError, OverflowError):
        first = today.replace(day=1)
    tasks = list(qs.filter(due_date__year=first.year, due_date__month=first.month))
    ranks = {'critical':0,'high':1,'normal':2,'low':3}
    tasks.sort(key=lambda task: (task.status in ['done','cancelled'], ranks.get(task.priority,2), task.title.casefold(), task.pk))
    grouped = {}
    for task in tasks: grouped.setdefault(task.due_date, []).append(task)
    try:
        selected = date.fromisoformat(request.GET.get('day',''))
        if (selected.year, selected.month) != (first.year, first.month): raise ValueError()
    except (ValueError, TypeError):
        selected = today if (today.year,today.month)==(first.year,first.month) else min(grouped,default=first)
    weeks = []
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(first.year,first.month):
        weeks.append([{'date':day,'in_month':day.month==first.month,'today':day==today,'selected':day==selected,'tasks':grouped.get(day,[]),'preview':grouped.get(day,[])[:2],'more':max(0,len(grouped.get(day,[]))-2)} for day in week])
    days = [{'date':date(first.year,first.month,number),'tasks':grouped.get(date(first.year,first.month,number),[]),'selected':date(first.year,first.month,number)==selected} for number in range(1,calendar.monthrange(first.year,first.month)[1]+1)]
    return {'month':first,'previous':first-timedelta(days=1),'following':(first+timedelta(days=32)).replace(day=1),'calendar_today':today,'calendar_selected':selected,'calendar_weeks':weeks,'calendar_days':days,'calendar_weekdays':WEEKDAYS,'calendar_task_count':len(tasks),'calendar_undated_count':qs.filter(due_date__isnull=True).count()}
