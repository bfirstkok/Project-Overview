from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Project, Task, Comment, Attachment, Team
from .permissions import projects_for, assignable_users, manage_task

class StyledForm:
    def style(self):
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-select' if isinstance(field.widget, (forms.Select, forms.SelectMultiple)) else 'form-control'
            if isinstance(field.widget, forms.Textarea): field.widget.attrs['rows'] = 4
            if isinstance(field, forms.DateField): field.widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d')

class ProjectForm(StyledForm, forms.ModelForm):
    version = forms.IntegerField(widget=forms.HiddenInput, required=False)
    class Meta:
        model = Project
        fields = ['title', 'customer', 'category', 'description', 'owner', 'members', 'status', 'start_date', 'due_date', 'document_url']
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['version'].initial = self.instance.version
        self.fields['version'].required = bool(self.instance.pk)
        from django.db.models import Q
        self.fields['owner'].queryset = User.objects.filter(Q(pk__in=assignable_users(user).values('pk')) | Q(pk=user.pk))
        self.fields['members'].queryset = assignable_users(user)
        if not user.is_manager: self.fields['owner'].queryset = User.objects.filter(pk=user.pk)
        self.fields['members'].help_text = 'กด Ctrl / Command เพื่อเลือกหลายคน'
        self.style()

class TaskForm(StyledForm, forms.ModelForm):
    version = forms.IntegerField(widget=forms.HiddenInput, required=False)
    class Meta:
        model = Task
        fields = ['title', 'project', 'description', 'sales', 'engineer', 'assignees', 'priority', 'status', 'start_date', 'due_date', 'progress', 'notes_to_colleague', 'work_notes']
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = projects_for(user)
        self.fields['version'].initial = self.instance.version
        self.fields['version'].required = bool(self.instance.pk)
        people = assignable_users(user)
        self.fields['assignees'].queryset = people
        self.fields['sales'].queryset = people.filter(role__in=[User.Role.SALES,User.Role.INTERN])
        self.fields['engineer'].queryset = people.filter(role__in=[User.Role.ENGINEER,User.Role.INTERN])
        if self.instance.pk:
            # Preserve existing assignees if an employee is deactivated or moves teams.
            # New assignments still come only from the active, authorized choices.
            from django.db.models import Q
            for name in ['sales', 'engineer']:
                current = getattr(self.instance, name + '_id')
                self.fields[name].queryset = User.objects.filter(Q(pk__in=self.fields[name].queryset.values('pk')) | Q(pk=current))
            self.fields['assignees'].queryset = User.objects.filter(Q(pk__in=people.values('pk')) | Q(pk__in=self.instance.assignees.values('pk')))
        if self.instance.pk and not manage_task(user, self.instance):
            for name in ['title', 'project', 'description', 'assignees', 'priority', 'start_date', 'due_date']: self.fields[name].disabled = True
            for name in ['sales', 'engineer']: self.fields[name].disabled = True
        self.fields['project'].help_text = 'เว้นว่างสำหรับงานส่วนตัว / งานทั่วไป'
        self.fields['assignees'].help_text = 'สมาชิกเพิ่มเติมนอกเหนือจาก Sales และ Engineer'
        self.fields['progress'].help_text = '0–100% แยกจาก Status โดยไม่เปลี่ยนสถานะอัตโนมัติ'
        self.fields['notes_to_colleague'].help_text = 'บันทึกสื่อสารระหว่าง Sales และ Engineer ทุกการแก้ไขมีประวัติ'
        self.style()
    def clean(self):
        data = super().clean()
        project = data.get('project')
        people = data.get('assignees')
        if project and people is not None:
            valid = set(project.members.values_list('pk', flat=True)) | {project.owner_id}
            if self.instance.pk and project.pk==self.instance.project_id:
                valid |= {pk for pk in [self.instance.sales_id,self.instance.engineer_id] if pk}
                valid |= set(self.instance.assignees.values_list('pk',flat=True))
            for field in ['sales', 'engineer']:
                if data.get(field) and data[field].pk not in valid: self.add_error(field, 'ต้องเป็นเจ้าของหรือสมาชิกโปรเจกต์ เพิ่มสมาชิกในโปรเจกต์ก่อน')
            if any(person.pk not in valid for person in people): self.add_error('assignees', 'ผู้รับผิดชอบต้องเป็นเจ้าของหรือสมาชิกโปรเจกต์')
        return data

class CommentForm(StyledForm, forms.ModelForm):
    class Meta: model = Comment; fields = ['body']
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs); self.style()

class AttachmentForm(StyledForm, forms.ModelForm):
    class Meta: model = Attachment; fields = ['file']
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs); self.style()

class CreateUserForm(StyledForm, forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'team', 'is_active']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        # Users authenticate with Microsoft; no local password is issued.
        self.fields.pop('password1', None); self.fields.pop('password2', None)
        self.style()
    def clean_email(self):
        from .sso import corporate_email
        return corporate_email(self.cleaned_data['email'])
    def save(self, commit=True):
        person = forms.ModelForm.save(self,commit=False)
        person.set_unusable_password()
        if commit: person.save(); self.save_m2m()
        return person

class EditUserForm(StyledForm, forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role', 'team', 'is_active']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.fields['email'].required=True; self.style()
    def clean_email(self):
        from .sso import corporate_email
        return corporate_email(self.cleaned_data['email'])

class TeamForm(StyledForm, forms.ModelForm):
    class Meta: model = Team; fields = ['name']
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs); self.style()
