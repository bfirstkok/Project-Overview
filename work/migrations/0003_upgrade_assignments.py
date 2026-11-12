from django.db import migrations

def upgrade(apps, schema_editor):
    Task = apps.get_model('work', 'Task')
    db = schema_editor.connection.alias
    Task.objects.using(db).filter(priority='medium').update(priority='normal')
    for task in Task.objects.using(db).prefetch_related('assignees').iterator(chunk_size=200):
        people = list(task.assignees.all())
        sales = next((p for p in people if p.role == 'sales'), None)
        engineer = next((p for p in people if p.role == 'engineer'), None)
        task.sales_id = sales.pk if sales else None
        task.engineer_id = engineer.pk if engineer else None
        task.save(using=db, update_fields=['sales', 'engineer'])
        task.assignees.remove(*[p for p in [sales, engineer] if p])

class Migration(migrations.Migration):
    dependencies = [('work', '0002_importbatch_and_more')]
    operations = [migrations.RunPython(upgrade, migrations.RunPython.noop)]
