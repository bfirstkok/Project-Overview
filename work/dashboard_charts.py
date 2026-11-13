"""Chart values built only from the caller's permission-filtered tasks."""
from datetime import timedelta
from django.db.models import Count
from .models import Status, Task

def dashboard_charts(tasks, workload, today):
    active = tasks.exclude(status__in=[Status.DONE,Status.CANCELLED])
    people = sorted(workload,key=lambda row:(-row['stats']['pending'],-row['stats']['overdue'],str(row['person']).casefold()))
    maximum = max((row['stats']['pending'] for row in people),default=0) or 1
    workload_chart = []
    for row in people:
        pending,overdue = row['stats']['pending'],row['stats']['overdue']
        workload_chart.append({**row,'on_time':pending-overdue,'on_time_width':round((pending-overdue)/maximum*100,3),'overdue_width':round(overdue/maximum*100,3)})
    counts = {row['priority']:row['count'] for row in active.values('priority').annotate(count=Count('pk',distinct=True)).order_by()}
    largest = max(counts.values(),default=0) or 1
    priority_chart = [{'key':key,'label':label,'count':counts.get(key,0),'width':round(counts.get(key,0)/largest*100,3)} for key,label in reversed(Task.Priority.choices)]
    end = today+timedelta(days=6)
    daily = {row['due_date']:row['count'] for row in active.filter(due_date__range=[today,end]).values('due_date').annotate(count=Count('pk',distinct=True)).order_by()}
    tallest = max(daily.values(),default=0) or 1
    due_chart = []
    for offset in range(7):
        day = today+timedelta(days=offset)
        count = daily.get(day,0)
        due_chart.append({'date':day,'count':count,'height':round(count/tallest*100,3),'today':offset==0})
    return {'workload_chart':workload_chart,'priority_chart':priority_chart,'due_chart':due_chart,'due_chart_total':sum(daily.values()),'due_chart_end':end}
