import os
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from work.models import Team, User, Project, Task, Status, Comment, Activity

class Command(BaseCommand):
    help = 'สร้างข้อมูลตัวอย่างจริงในฐานข้อมูล (ใช้ DEMO_PASSWORD จาก environment) ไม่แก้ไขผู้ใช้เดิม'
    @transaction.atomic
    def handle(self, *args, **options):
        password = os.getenv('DEMO_PASSWORD')
        if not password: raise CommandError('Set DEMO_PASSWORD environment variable first')
        from django.contrib.auth.password_validation import validate_password
        validate_password(password)
        team, _ = Team.objects.get_or_create(name='Sales & Engineering')
        accounts = [('demo.admin', 'ภัทร', 'ผู้ดูแลระบบ', 'admin'), ('demo.manager', 'กานต์', 'ผู้จัดการ', 'manager'), ('demo.sales', 'ณัฐ', 'ฝ่ายขาย', 'sales'), ('demo.engineer', 'ธนา', 'วิศวกร', 'engineer'), ('demo.presales', 'พิม', 'วิศวกรก่อนขาย', 'engineer')]
        people = []
        for username, first, last, role in accounts:
            user, created = User.objects.get_or_create(username=username, defaults={'first_name': first, 'last_name': last, 'role': role, 'team': team})
            if created: user.set_password(password); user.save()
            people.append(user)
        admin, manager, sales, engineer, presales = people
        if Project.objects.filter(title='ปรับปรุงระบบ Network สำนักงานใหญ่', owner=manager).exists():
            self.stdout.write('Demo data already exists; no duplicate projects created.'); return
        today = timezone.localdate()
        specs = [('ปรับปรุงระบบ Network สำนักงานใหญ่', 'บริษัท เอเชีย เทคโนโลยี จำกัด', 'network', 'progress'), ('ย้ายระบบขึ้น Cloud Infrastructure', 'บริษัท นอร์ทสตาร์ โซลูชัน จำกัด', 'cloud', 'progress'), ('ติดตั้ง Server & Backup', 'บริษัท พรีซิชั่น อินดัสทรี จำกัด', 'server', 'todo'), ('พัฒนาระบบภายในองค์กร', 'Askme Internal', 'internal', 'progress')]
        projects = []
        for title, customer, category, status in specs:
            project = Project.objects.create(title=title, customer=customer, category=category, status=status, owner=manager, start_date=today-timedelta(days=14), due_date=today+timedelta(days=24), description='ประสานงานฝ่ายขายและวิศวกร ตั้งแต่เก็บความต้องการ ออกแบบโซลูชัน จัดเตรียมเอกสาร และติดตั้งส่งมอบงานให้ลูกค้า')
            project.members.set([sales, engineer, presales]); projects.append(project)
            Activity.objects.create(actor=manager, project=project, summary=f'สร้างโปรเจกต์ {title} (ข้อมูลตัวอย่าง)')
        task_specs = [('สำรวจหน้างานและเก็บ Requirement',0,sales,'done',100,'high',-5), ('ออกแบบ Network Diagram',0,presales,'progress',65,'high',2), ('จัดทำ BOM และ Proposal',0,sales,'progress',40,'high',1), ('ติดตั้งและทดสอบ Core Switch',0,engineer,'todo',0,'normal',8), ('ประเมินค่าใช้จ่าย Cloud',1,presales,'progress',75,'critical',-2), ('วางแผนย้าย Virtual Machine',1,engineer,'hold',25,'normal',5), ('ยืนยันขอบเขตงานกับลูกค้า',1,sales,'done',100,'normal',-1), ('จัดเตรียมอุปกรณ์ Server',2,engineer,'todo',0,'high',3), ('ออกแบบนโยบาย Backup',2,presales,'progress',35,'normal',4), ('ทดสอบการกู้คืนข้อมูล',2,engineer,'todo',0,'normal',12), ('สรุปรายงานประชุมประจำสัปดาห์',3,sales,'done',100,'low',-3), ('ปรับปรุงเอกสารส่งมอบงาน',3,presales,'progress',55,'normal',-1), ('ตรวจสอบอุปกรณ์ห้อง Server',3,engineer,'todo',0,'low',6)]
        for title, idx, person, status, progress, priority, days in task_specs:
            task = Task.objects.create(title=title, project=projects[idx], creator=manager, status=status, progress=progress, priority=priority, start_date=today-timedelta(days=10), due_date=today+timedelta(days=days), description='ข้อมูลตัวอย่างสำหรับทดลองระบบ สามารถแก้ไขและอัปเดตงานเพื่อทดสอบได้', work_notes='ประสานงานกับทีมและรวบรวมข้อมูลที่เกี่ยวข้องแล้ว' if progress else '')
            if person.role=='sales': task.sales=person
            elif person.role=='engineer': task.engineer=person
            else: task.assignees.add(person)
            task.save()
            Activity.objects.create(actor=person, task=task, summary=f'อัปเดต {title}: {task.get_status_display()} ความคืบหน้า {progress}% (ข้อมูลตัวอย่าง)')
        Comment.objects.create(task=Task.objects.filter(project=projects[0]).first(), author=manager, body='รบกวนอัปเดตผลการดำเนินงานและเอกสารที่เกี่ยวข้องในระบบด้วยครับ (ข้อมูลตัวอย่าง)')
        self.stdout.write(self.style.SUCCESS('Created demo users, 4 projects and 13 tasks. Password was read from environment.'))
