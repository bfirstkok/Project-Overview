import uuid
from pathlib import Path
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

class Team(models.Model):
    name = models.CharField('ชื่อทีม', max_length=120, unique=True)
    def __str__(self): return self.name

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        MANAGER = 'manager', 'Manager'
        SALES = 'sales', 'Sales'
        ENGINEER = 'engineer', 'Engineer'
    role = models.CharField('บทบาท', max_length=12, choices=Role.choices, default=Role.ENGINEER)
    team = models.ForeignKey(Team, verbose_name='ทีม', null=True, blank=True, on_delete=models.SET_NULL)
    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'), condition=~Q(email=''), name='user_unique_nonempty_email')]
    @property
    def is_admin(self): return self.is_superuser or self.role == self.Role.ADMIN
    @property
    def is_manager(self): return self.is_admin or self.role == self.Role.MANAGER
    def __str__(self): return self.get_full_name() or self.username

class Status(models.TextChoices):
    TODO = 'todo', 'To Do'
    PROGRESS = 'progress', 'In Progress'
    HOLD = 'hold', 'On Hold'
    DONE = 'done', 'Complete'
    CANCELLED = 'cancelled', 'Cancelled'

class DatedWork(models.Model):
    title = models.CharField('ชื่อ', max_length=200)
    description = models.TextField('รายละเอียด', blank=True)
    status = models.CharField('สถานะ', max_length=12, choices=Status.choices, default=Status.TODO)
    start_date = models.DateField('วันเริ่มต้น', null=True, blank=True)
    due_date = models.DateField('กำหนดเสร็จ', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1, editable=False)
    class Meta:
        abstract = True
        ordering = ['-created_at']
        constraints = [models.CheckConstraint(condition=Q(due_date__gte=models.F('start_date')) | Q(start_date__isnull=True) | Q(due_date__isnull=True), name='%(class)s_valid_dates')]
    def clean(self):
        super().clean()
        if self.start_date and self.due_date and self.due_date < self.start_date and not getattr(self, 'source_date_exception', False):
            raise ValidationError({'due_date': 'กำหนดเสร็จต้องไม่ก่อนวันเริ่มต้น'})
    def __str__(self): return self.title

class Project(DatedWork):
    class Category(models.TextChoices):
        NETWORK = 'network', 'Network'
        SERVER = 'server', 'Server'
        CLOUD = 'cloud', 'Cloud'
        AI = 'ai', 'AI'
        SOLUTION = 'solution', 'IT Solution'
        INTERNAL = 'internal', 'Internal'
    customer = models.CharField('ลูกค้า / บริษัท', max_length=200, blank=True)
    category = models.CharField('ประเภทงาน', max_length=12, choices=Category.choices, default=Category.SOLUTION)
    owner = models.ForeignKey(User, verbose_name='ผู้รับผิดชอบหลัก', on_delete=models.PROTECT, related_name='owned_projects')
    members = models.ManyToManyField(User, verbose_name='สมาชิกทีม', blank=True, related_name='projects')
    document_url = models.URLField('ลิงก์เอกสาร BOM / Proposal', blank=True)
    @property
    def progress(self):
        return round(self.tasks.aggregate(value=models.Avg('progress'))['value'] or 0)

class Task(DatedWork):
    source_number = models.PositiveIntegerField(null=True, blank=True, editable=False)
    source_data = models.JSONField(default=dict, blank=True, editable=False)
    source_date_exception = models.BooleanField(default=False, editable=False)
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'
    project = models.ForeignKey(Project, verbose_name='โปรเจกต์', null=True, blank=True, on_delete=models.PROTECT, related_name='tasks')
    creator = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_tasks')
    assignees = models.ManyToManyField(User, verbose_name='สมาชิกเพิ่มเติม', related_name='tasks', blank=True)
    sales = models.ForeignKey(User, verbose_name='Sales', null=True, blank=True, on_delete=models.PROTECT, related_name='sales_tasks')
    engineer = models.ForeignKey(User, verbose_name='Engineer', null=True, blank=True, on_delete=models.PROTECT, related_name='engineering_tasks')
    notes_to_colleague = models.TextField('Notes to Colleague', blank=True, max_length=5000)
    priority = models.CharField('ความสำคัญ', max_length=12, choices=Priority.choices, default=Priority.NORMAL)
    progress = models.PositiveSmallIntegerField('ความคืบหน้า (%)', default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    work_notes = models.TextField('บันทึกการทำงาน', blank=True)
    class Meta(DatedWork.Meta):
        indexes = [models.Index(fields=['status', 'due_date']), models.Index(fields=['priority'])]
        constraints = [models.CheckConstraint(condition=Q(due_date__gte=models.F('start_date')) | Q(start_date__isnull=True) | Q(due_date__isnull=True) | Q(source_date_exception=True), name='task_valid_dates'), models.CheckConstraint(condition=Q(progress__lte=100), name='task_progress_max')]
    def clean(self):
        super().clean()
        if self.source_date_exception and self.pk and self.start_date and self.due_date and self.due_date < self.start_date:
            original = Task.objects.filter(pk=self.pk).values('start_date','due_date','source_date_exception').first()
            if not original or not original['source_date_exception'] or (self.start_date,self.due_date)!=(original['start_date'],original['due_date']):
                raise ValidationError({'due_date':'วันที่ใหม่ต้องไม่สิ้นสุดก่อนวันเริ่ม ยกเว้นค่าต้นฉบับที่นำเข้าไว้'})
    @property
    def register_number(self): return self.source_number or self.pk
    @property
    def overdue(self): return bool(self.due_date and self.due_date < timezone.localdate() and self.status not in [Status.DONE, Status.CANCELLED])

class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    body = models.TextField('ความคิดเห็น', max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['created_at']

def upload_path(instance, filename):
    return f'attachments/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'

def validate_file_size(value):
    if value.size > 5 * 1024 * 1024: raise ValidationError('ไฟล์ต้องมีขนาดไม่เกิน 5 MB')

class Attachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments', null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='attachments', null=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    file = models.FileField('ไฟล์แนบ', upload_to=upload_path, validators=[validate_file_size, FileExtensionValidator(['pdf', 'xlsx', 'xls', 'docx', 'csv', 'txt', 'png', 'jpg', 'jpeg', 'zip'])])
    original_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=(Q(task__isnull=False, project__isnull=True) | Q(task__isnull=True, project__isnull=False)), name='attachment_exactly_one_parent')]

class Activity(models.Model):
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL)
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']

class LoginAttempt(models.Model):
    ip_hash = models.CharField(max_length=64, db_index=True)
    key_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

class ImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    payload = models.JSONField()
    mapping = models.JSONField(default=dict)
    options = models.JSONField(default=dict)
    preview = models.JSONField(default=list)
    revision = models.PositiveIntegerField(default=1)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
