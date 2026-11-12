import io
import tempfile
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook
from .models import Team, Project, Task, Status, Activity, Attachment, Comment, LoginAttempt
from .permissions import tasks_for, projects_for

User = get_user_model()

@override_settings(DEBUG=True, ALLOW_LOCAL_LOGIN=True, SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class WorkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user('admin', password='Test-Password-582!', role='admin')
        cls.manager = User.objects.create_user('manager', password='Test-Password-582!', role='manager')
        cls.sales = User.objects.create_user('sales', password='Test-Password-582!', role='sales')
        cls.engineer = User.objects.create_user('engineer', password='Test-Password-582!', role='engineer')
        cls.other = User.objects.create_user('outsider', password='Test-Password-582!', role='engineer')
        team=Team.objects.create(name='Test team')
        User.objects.all().update(team=team)
        for person in [cls.admin,cls.manager,cls.sales,cls.engineer,cls.other]: person.refresh_from_db()
        cls.project = Project.objects.create(title='Network upgrade', customer='Acme', owner=cls.sales)
        cls.project.members.add(cls.engineer)
        cls.task = Task.objects.create(title='Install switch', creator=cls.sales, project=cls.project)
        cls.task.assignees.add(cls.engineer)
        cls.private = Task.objects.create(title='Private task', creator=cls.other)
    def login(self, user=None): self.client.force_login(user or self.sales)
    def task_data(self, **overrides):
        data = {'title': self.task.title, 'project': self.project.pk, 'assignees': [self.engineer.pk], 'priority': 'normal', 'status': 'progress', 'progress': 40, 'description': 'Updated requirements', 'work_notes': 'Installed cables', 'version': self.task.version}
        data.update(overrides); return data

    def test_anonymous_redirects(self):
        for url in ['/', '/projects/', '/tasks/', '/team/', '/reports/', '/activity/', '/users/', f'/tasks/{self.task.pk}/']:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code, 302)

    def test_valid_login_and_post_logout(self):
        response = self.client.post('/login/', {'username': 'sales', 'password': 'Test-Password-582!'})
        self.assertRedirects(response, '/')
        self.assertEqual(self.client.get('/logout/').status_code, 405)
        self.assertRedirects(self.client.post('/logout/'), '/login/')

    def test_login_throttle(self):
        for _ in range(5): self.client.post('/login/', {'username': 'sales', 'password': 'wrong'})
        self.assertEqual(self.client.post('/login/', {'username': 'sales', 'password': 'wrong'}).status_code, 429)

    def test_login_next_cannot_redirect_external(self):
        response = self.client.post('/login/', {'username': 'sales', 'password': 'Test-Password-582!', 'next': 'https://evil.example/'})
        self.assertEqual(response.url, '/')

    def test_scope_of_project_and_personal_tasks(self):
        self.assertIn(self.task, tasks_for(self.engineer))
        self.assertNotIn(self.private, tasks_for(self.engineer))
        self.assertNotIn(self.project, projects_for(self.other))
        self.assertIn(self.private, tasks_for(self.manager))

    def test_member_can_render_every_core_view(self):
        self.login(self.engineer)
        for url in ['/', '/projects/', f'/projects/{self.project.pk}/', '/tasks/', '/tasks/?view=kanban', '/tasks/?view=calendar', '/tasks/?view=calendar&month=invalid', f'/tasks/{self.task.pk}/', f'/tasks/{self.task.pk}/edit/', '/tasks/new/', '/projects/new/', '/reports/', '/activity/', '/password/']:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code, 200)

    def test_outsider_cannot_read_or_edit(self):
        self.login(self.other)
        for url in [f'/tasks/{self.task.pk}/', f'/projects/{self.project.pk}/', f'/tasks/{self.task.pk}/edit/', f'/projects/{self.project.pk}/edit/']:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code, 404)

    def test_non_admin_cannot_manage_users(self):
        for user in [self.sales, self.engineer, self.manager]:
            self.login(user)
            for url in ['/users/', '/users/new/', f'/users/{self.other.pk}/edit/', f'/users/{self.other.pk}/password/', '/teams/new/']:
                with self.subTest(user=user, url=url): self.assertEqual(self.client.get(url).status_code, 403)

    def test_team_view_restricted_to_managers(self):
        self.login(); self.assertEqual(self.client.get('/team/').status_code, 403)
        self.login(self.manager); self.assertEqual(self.client.get('/team/').status_code, 200)

    def test_admin_creates_user_and_team(self):
        self.login(self.admin)
        self.assertEqual(self.client.post('/teams/new/', {'name': 'Engineering'}).status_code, 302)
        response = self.client.post('/users/new/', {'email':'newperson@askme.co.th','username': 'newperson', 'role': 'engineer', 'is_active': 'on', 'password1': 'Strong-New-Password-437!', 'password2': 'Strong-New-Password-437!'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.get(username='newperson').has_usable_password())
        self.assertEqual(self.client.get('/users/').status_code, 200)

    def test_admin_cannot_disable_self(self):
        self.login(self.admin)
        response = self.client.post(f'/users/{self.admin.pk}/edit/', {'email':'admin@askme.co.th','role': 'engineer', 'is_active': ''})
        self.assertEqual(response.status_code, 200)
        self.admin.refresh_from_db(); self.assertTrue(self.admin.is_active); self.assertEqual(self.admin.role, 'admin')

    def test_create_project_and_history(self):
        self.login()
        response = self.client.post('/projects/new/', {'title': 'New project', 'customer': 'Customer', 'category': 'cloud', 'owner': self.sales.pk, 'members': [self.engineer.pk], 'status': 'todo'})
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(title='New project')
        self.assertTrue(project.members.filter(pk=self.engineer.pk).exists())
        self.assertTrue(Activity.objects.filter(project=project).exists())

    def test_project_changes_include_before_and_after(self):
        self.login()
        response = self.client.post(f'/projects/{self.project.pk}/edit/', {'version':self.project.version,'title': 'New project title', 'customer': 'Acme', 'category': 'network', 'owner': self.sales.pk, 'members': [self.engineer.pk], 'status': 'progress'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('Network upgrade → New project title', Activity.objects.latest('id').summary)

    def test_member_cannot_edit_project(self):
        self.login(self.engineer)
        self.assertEqual(self.client.post(f'/projects/{self.project.pk}/edit/', {}).status_code, 403)

    def test_regular_user_cannot_assign_project_owner_to_other(self):
        self.login()
        response = self.client.post('/projects/new/', {'title': 'Bad owner', 'customer': 'Customer', 'category': 'cloud', 'owner': self.other.pk, 'status': 'todo'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Project.objects.filter(title='Bad owner').exists())

    def test_create_multiple_assignment_and_personal_task(self):
        self.login()
        response = self.client.post('/tasks/new/', self.task_data(title='New task', assignees=[self.sales.pk, self.engineer.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Task.objects.get(title='New task').assignees.count(), 2)
        response = self.client.post('/tasks/new/', self.task_data(title='Personal', project='', assignees=[]))
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(Task.objects.get(title='Personal').project)

    def test_cannot_assign_outsider_to_project(self):
        self.login()
        response = self.client.post('/tasks/new/', self.task_data(title='Not allowed', assignees=[self.other.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.filter(title='Not allowed').exists())

    def test_assignee_updates_progress_but_cannot_reassign_or_rename(self):
        self.login(self.engineer)
        response = self.client.post(f'/tasks/{self.task.pk}/edit/', self.task_data(title='Tampered title', assignees=[self.other.pk], priority='critical', project='', progress=70))
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Install switch'); self.assertEqual(self.task.progress, 70)
        self.assertEqual(self.task.project_id, self.project.pk); self.assertEqual(self.task.priority, 'normal')
        self.assertEqual(list(self.task.assignees.all()), [self.engineer])
        self.assertIn('0 → 70', Activity.objects.latest('id').summary)

    def test_status_and_progress_are_independent(self):
        self.login(self.engineer)
        response = self.client.post(f'/tasks/{self.task.pk}/edit/', self.task_data(status='done', progress=50))
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db(); self.assertEqual(self.task.progress, 50)
        self.assertEqual(self.project.progress, 50)

    def test_invalid_dates_and_progress_rejected(self):
        self.login()
        for override in [{'start_date': '2026-11-20', 'due_date': '2026-11-01'}, {'progress': 101}, {'progress': -1}]:
            with self.subTest(override=override):
                response = self.client.post('/tasks/new/', self.task_data(title='Invalid', **override))
                self.assertEqual(response.status_code, 200); self.assertFalse(Task.objects.filter(title='Invalid').exists())

    def test_db_constraints(self):
        with self.assertRaises(IntegrityError), transaction.atomic(): Task.objects.create(title='Invalid', creator=self.sales, progress=101)

    def test_comment_and_escape(self):
        self.login(self.engineer)
        self.client.post(f'/tasks/{self.task.pk}/comments/', {'body': '<script>alert(1)</script>'})
        self.assertTrue(Comment.objects.filter(task=self.task).exists())
        self.assertContains(self.client.get(f'/tasks/{self.task.pk}/'), '&lt;script&gt;')
        self.assertTrue(Activity.objects.filter(task=self.task, summary__contains='แสดงความคิดเห็น').exists())

    def test_comment_denied_to_outsider(self):
        self.login(self.other)
        self.assertEqual(self.client.post(f'/tasks/{self.task.pk}/comments/', {'body': 'forbidden'}).status_code, 404)

    def test_upload_and_protected_download(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            self.login(self.engineer)
            response = self.client.post(f'/tasks/{self.task.pk}/upload/', {'file': SimpleUploadedFile('proposal.pdf', b'%PDF-1.7 test', content_type='application/pdf')})
            self.assertEqual(response.status_code, 302)
            item = Attachment.objects.get(task=self.task)
            response = self.client.get(f'/attachments/{item.pk}/')
            self.assertEqual(response.status_code, 200); self.assertIn('attachment;', response['Content-Disposition'])
            self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.7 test')
            self.login(self.other); self.assertEqual(self.client.get(f'/attachments/{item.pk}/').status_code, 404)
            self.assertEqual(self.client.get('/media/' + item.file.name).status_code, 404)

    def test_executable_and_oversized_upload_rejected(self):
        self.login(self.engineer)
        for name, data in [('bad.html', b'<script>bad</script>'), ('large.pdf', b'x' * (5 * 1024 * 1024 + 1))]:
            with self.subTest(name=name):
                self.client.post(f'/tasks/{self.task.pk}/upload/', {'file': SimpleUploadedFile(name, data)})
                self.assertFalse(Attachment.objects.exists())

    def test_reports_filters_and_formula_safe_exports(self):
        self.task.title = '=HYPERLINK("http://evil")'; self.task.save()
        self.login(self.engineer)
        response = self.client.get('/reports/?export=csv')
        self.assertContains(response, "'=HYPERLINK")
        self.assertNotContains(response, 'Private task')
        response = self.client.get('/reports/?export=xlsx')
        book = load_workbook(io.BytesIO(response.content))
        self.assertTrue(book.active['C2'].value.startswith('=HYPERLINK'))
        self.assertEqual(book.active['C2'].data_type, 's')
        response = self.client.get('/reports/?status=done&export=csv')
        self.assertNotContains(response, 'HYPERLINK')

    def test_dashboard_counts_real_database(self):
        self.task.due_date = timezone.localdate() - timedelta(days=1); self.task.priority = 'high'; self.task.save()
        self.login(self.engineer)
        response = self.client.get('/dashboard/')
        self.assertEqual(response.context['summary']['total'], 1)
        self.assertEqual(response.context['summary']['overdue'], 1)
        self.assertEqual(response.context['summary']['high'], 1)

    def test_delete_permissions_and_retained_history(self):
        self.login(self.engineer)
        self.assertEqual(self.client.post(f'/tasks/{self.task.pk}/delete/', {'version':self.task.version}).status_code, 403)
        self.login()
        self.assertEqual(self.client.get(f'/tasks/{self.task.pk}/delete/').status_code, 200)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())
        self.client.post(f'/tasks/{self.task.pk}/delete/', {'version':self.task.version})
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())
        self.assertTrue(Activity.objects.filter(summary__contains='Install switch', task__isnull=True).exists())

    def test_project_with_tasks_cannot_be_deleted(self):
        self.login()
        self.client.post(f'/projects/{self.project.pk}/delete/', {'version':self.project.version})
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_csrf_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.sales,backend='work.sso.LocalDevelopmentBackend')
        self.assertEqual(client.post('/tasks/new/', self.task_data()).status_code, 403)

    def test_get_mutations_forbidden(self):
        self.login()
        for url in [f'/tasks/{self.task.pk}/comments/', f'/tasks/{self.task.pk}/upload/', f'/projects/{self.project.pk}/upload/']:
            self.assertEqual(self.client.get(url).status_code, 405)

    def test_inactive_user_cannot_login(self):
        self.other.is_active=False; self.other.save()
        self.assertFalse(self.client.login(username='outsider', password='Test-Password-582!'))

    def test_filters(self):
        self.login(self.engineer)
        for query in ['q=Install', f'project={self.project.pk}', f'assignees={self.engineer.pk}', 'mine=1', 'status=todo', 'priority=normal']:
            with self.subTest(query=query): self.assertContains(self.client.get('/tasks/?'+query), 'Install switch')
        self.assertNotContains(self.client.get('/tasks/?q=Nonexistent'), 'Install switch')

    def test_calendar_extreme_dates_do_not_crash(self):
        self.login()
        for year, month in [(9999,12),(1,1),(2026,99),(-1,-1)]:
            with self.subTest(year=year,month=month): self.assertEqual(self.client.get(f'/tasks/?view=calendar&year={year}&month={month}').status_code,200)

    def test_pagination_preserves_filter_query(self):
        self.login()
        Task.objects.bulk_create([Task(title=f'Pagination task {i}', creator=self.sales) for i in range(25)])
        response = self.client.get('/tasks/?q=Pagination')
        self.assertContains(response, 'q=Pagination&amp;page=2')
        self.assertNotContains(response, 'href="??')
        self.assertEqual(len(self.client.get('/tasks/?q=Pagination&page=2').context['page']),5)

    def test_manager_can_edit_unassigned_task(self):
        self.login(self.manager)
        response = self.client.post(f'/tasks/{self.private.pk}/edit/', self.task_data(title='Manager updated personal task',project='',assignees=[self.other.pk]))
        self.assertEqual(response.status_code,302)
        self.private.refresh_from_db(); self.assertEqual(self.private.title,'Manager updated personal task')
