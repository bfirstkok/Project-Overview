import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from unittest.mock import patch
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, RequestFactory, override_settings, skipUnlessDBFeature
from django.utils import timezone
from openpyxl import Workbook, load_workbook
from allauth.socialaccount.models import SocialLogin, SocialAccount
from allauth.core.exceptions import ImmediateHttpResponse
from .models import User, Team, Project, Task, Activity, ImportBatch
from .permissions import tasks_for, edit_task
from .services import save_work, EditConflict
from .excel import COLUMNS, read_xlsx, initial_mapping, preview_rows, commit_batch, person_controls, person_key
from .sso import CorporateSocialAdapter

@override_settings(DEBUG=True, ALLOW_LOCAL_LOGIN=True, SECURE_SSL_REDIRECT=False)
class ExcelWorkflows(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team=Team.objects.create(name='Team A'); cls.other_team=Team.objects.create(name='Team B')
        cls.admin=User.objects.create_user('admin',role='admin',email='testadmin@askme.co.th',team=cls.team)
        cls.manager=User.objects.create_user('manager',role='manager',email='testmanager@askme.co.th',team=cls.team)
        cls.sales=User.objects.create_user('sales',first_name='Sales',last_name='Tester',role='sales',email='testsales@askme.co.th',team=cls.team)
        cls.engineer=User.objects.create_user('engineer',first_name='Engineer',last_name='Tester',role='engineer',email='testengineer@askme.co.th',team=cls.team)
        cls.outsider=User.objects.create_user('outsider',role='engineer',email='testoutsider@askme.co.th',team=cls.other_team)
        cls.project=Project.objects.create(title='Test project',customer='Test customer',owner=cls.manager)
        cls.project.members.add(cls.sales,cls.engineer)
        cls.task=Task.objects.create(title='Test task',creator=cls.manager,project=cls.project,sales=cls.sales,engineer=cls.engineer)
    def login(self,user=None): self.client.force_login(user or self.manager,backend='work.sso.LocalDevelopmentBackend')
    def excel(self,rows,headers=None):
        book=Workbook();sheet=book.active;sheet.append(headers or [label for key,label in COLUMNS])
        for row in rows:sheet.append(row)
        output=io.BytesIO();book.save(output)
        return SimpleUploadedFile('test-only.xlsx',output.getvalue(),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    def row(self,**changes):
        values={'no':'','project':self.project.title,'title':'New imported task','priority':'Normal','status':'In Progress','start_date':'01/11/2569','due_date':'15/11/2569','progress':45,'sales':'sales','engineer':'engineer','notes_to_colleague':'Test message, not company data'}
        values.update(changes);return [values[key] for key,label in COLUMNS]
    def batch(self,rows,**options):
        payload=read_xlsx(self.excel(rows))
        return ImportBatch.objects.create(owner=self.manager,filename='test-only.xlsx',payload=payload,mapping=initial_mapping(payload),options=options)
    def inline(self,field,value,version=None,user=None):
        self.login(user)
        return self.client.post(f'/tasks/{self.task.pk}/inline/',json.dumps({'field':field,'value':value,'version':version if version is not None else self.task.version}),content_type='application/json')
    def grid(self, rows, user=None):
        self.login(user)
        return self.client.post('/tasks/grid/',json.dumps({'rows':rows}),content_type='application/json')
    def test_grid_saves_combined_dates_and_independent_status(self):
        self.task.start_date=date(2026,11,1); self.task.due_date=date(2026,11,2); self.task.save()
        response=self.grid([{'id':self.task.pk,'version':1,'changes':{'start_date':'2026-12-01','due_date':'2026-12-02','progress':100,'status':'hold'}}])
        self.assertEqual(response.status_code,200)
        self.task.refresh_from_db()
        self.assertEqual((self.task.progress,self.task.status,self.task.version),(100,'hold',2))
        self.assertEqual(self.task.start_date,date(2026,12,1))
    def test_grid_rolls_back_all_rows_and_activity_on_validation_error(self):
        second=Task.objects.create(title='Second',creator=self.manager)
        count=Activity.objects.count()
        response=self.grid([{'id':self.task.pk,'version':1,'changes':{'progress':25}},{'id':second.pk,'version':1,'changes':{'progress':101}}])
        self.assertEqual(response.status_code,422)
        self.task.refresh_from_db(); self.assertEqual(self.task.progress,0)
        self.assertEqual(Activity.objects.count(),count)
    def test_grid_conflict_rolls_back_earlier_row(self):
        second=Task.objects.create(title='Second',creator=self.manager,version=2)
        response=self.grid([{'id':self.task.pk,'version':1,'changes':{'progress':25}},{'id':second.pk,'version':1,'changes':{'progress':50}}])
        self.assertEqual(response.status_code,409)
        self.task.refresh_from_db(); self.assertEqual(self.task.progress,0)
    def test_grid_rejects_forbidden_fields_and_other_team(self):
        response=self.grid([{'id':self.task.pk,'version':1,'changes':{'title':'Forbidden'}}],self.engineer)
        self.assertEqual(response.status_code,403)
        other=Task.objects.create(title='Private',creator=self.outsider)
        self.assertEqual(self.grid([{'id':other.pk,'version':1,'changes':{'progress':25}}]).status_code,403)
    def test_grid_rejects_duplicate_rows_without_saving(self):
        row={'id':self.task.pk,'version':1,'changes':{'progress':25}}
        self.assertEqual(self.grid([row,row]).status_code,422)
        self.task.refresh_from_db(); self.assertEqual(self.task.version,1)
    def test_calendar_selected_day_and_preview_keep_all_tasks(self):
        self.task.due_date=date(2026,11,12); self.task.save()
        for number in range(3): Task.objects.create(title=f'Daily task {number}',creator=self.manager,due_date=date(2026,11,12))
        self.login()
        response=self.client.get('/tasks/?view=calendar&year=2026&month=11&day=2026-11-12')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['calendar_selected'],date(2026,11,12))
        cell=next(c for week in response.context['calendar_weeks'] for c in week if c['date']==date(2026,11,12))
        self.assertEqual((len(cell['tasks']),len(cell['preview']),cell['more']),(4,2,2))
        self.assertContains(response,'Daily task 2')
    def test_calendar_preserves_permission_scope(self):
        Task.objects.create(title='Hidden calendar task',creator=self.outsider,due_date=date(2026,11,12))
        self.login()
        response=self.client.get('/tasks/?view=calendar&year=2026&month=11&day=invalid')
        self.assertEqual(response.status_code,200)
        self.assertNotContains(response,'Hidden calendar task')
        self.assertEqual(response.context['calendar_task_count'],0)
    def test_legacy_dates_preserved_but_new_invalid_dates_rejected(self):
        self.task.start_date=date(2026,4,29); self.task.due_date=date(2026,3,31)
        self.task.source_date_exception=True; self.task.source_number=61; self.task.save()
        self.assertEqual(self.inline('progress',50).status_code,200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.due_date,date(2026,3,31))
        self.assertEqual(self.inline('due_date','2026-03-30').status_code,422)
        self.assertEqual(self.inline('due_date','2026-05-01').status_code,200)
    def test_source_number_filter_and_order(self):
        self.task.source_number=400; self.task.save()
        self.login()
        response=self.client.get('/tasks/?no=400')
        self.assertEqual(list(response.context['page']),[self.task])
    def test_engineer_filter_and_dashboard_include_additional_members(self):
        self.task.engineer=None; self.task.save(); self.task.assignees.add(self.engineer)
        self.login()
        self.assertEqual(list(self.client.get(f'/tasks/?engineer={self.engineer.pk}').context['page']),[self.task])
        summary=self.client.get('/dashboard/').context['engineer_rows']
        self.assertEqual(next(row['stats']['total'] for row in summary if row['person']==self.engineer),1)
    def test_primary_sales_and_engineer_can_update(self):
        for person in [self.sales,self.engineer]:
            with self.subTest(person=person):
                self.assertIn(self.task,tasks_for(person));self.assertTrue(edit_task(person,self.task))
                response=self.inline('notes_to_colleague',f'Note from {person.username}',user=person)
                self.assertEqual(response.status_code,200)
                self.task.refresh_from_db()
        self.assertTrue(Activity.objects.filter(summary__contains='Notes to Colleague').exists())
    def test_manager_cannot_read_or_modify_other_team(self):
        other=Task.objects.create(title='Other team private task',creator=self.outsider,engineer=self.outsider)
        self.login();self.assertEqual(self.client.get(f'/tasks/{other.pk}/').status_code,404)
        response=self.client.post(f'/tasks/{other.pk}/inline/',json.dumps({'field':'progress','value':55,'version':1}),content_type='application/json')
        self.assertEqual(response.status_code,404)
        self.login(self.admin);self.assertEqual(self.client.get(f'/tasks/{other.pk}/').status_code,200)
    def test_progress_does_not_change_status(self):
        self.assertEqual(self.inline('progress',100).status_code,200)
        self.task.refresh_from_db();self.assertEqual(self.task.status,'todo');self.assertEqual(self.task.progress,100)
    def test_complete_does_not_change_progress(self):
        self.assertEqual(self.inline('status','done').status_code,200)
        self.task.refresh_from_db();self.assertEqual(self.task.progress,0)
    def test_cancelled_is_not_overdue_or_pending(self):
        self.task.due_date=timezone.localdate()-timedelta(days=2);self.task.save()
        self.assertEqual(self.inline('status','cancelled').status_code,200)
        self.task.refresh_from_db();self.assertFalse(self.task.overdue)
        self.login();self.assertEqual(self.client.get('/dashboard/').context['summary']['pending'],0)
    def test_inline_conflict_preserves_first_change(self):
        first=self.inline('progress',30,version=1);self.assertEqual(first.status_code,200)
        second=self.inline('progress',90,version=1);self.assertEqual(second.status_code,409)
        self.task.refresh_from_db();self.assertEqual(self.task.progress,30);self.assertEqual(self.task.version,2)
    def test_full_form_conflict(self):
        self.inline('progress',30)
        self.login();response=self.client.post(f'/tasks/{self.task.pk}/edit/',{'version':1,'title':'Stale edit','project':self.project.pk,'priority':'normal','status':'todo','progress':90})
        self.assertEqual(response.status_code,409)
        self.task.refresh_from_db();self.assertEqual(self.task.title,'Test task')
    def test_inline_rejects_reassignment_by_primary_assignee(self):
        self.assertEqual(self.inline('engineer',self.outsider.pk,user=self.sales).status_code,403)
        self.assertEqual(self.inline('title','Tamper',user=self.engineer).status_code,403)
    def test_invalid_inline_values_and_dates(self):
        for field,value in [('progress',101),('status','bogus'),('priority','medium')]:
            with self.subTest(field=field): self.assertEqual(self.inline(field,value).status_code,422)
    def test_inline_assignment_rejects_wrong_role_and_nonmember(self):
        self.assertEqual(self.inline('sales',self.engineer.pk).status_code,422)
        self.assertEqual(self.inline('engineer',self.outsider.pk,user=self.admin).status_code,422)
    def test_main_page_is_eleven_column_table(self):
        self.login();response=self.client.get('/')
        for key,label in COLUMNS:self.assertContains(response,label)
        self.assertContains(response,'data-update-url=')
    def test_task_page_size_uses_bounded_choices(self):
        self.login()
        self.assertEqual(self.client.get('/tasks/?per_page=100').context['page'].paginator.per_page,100)
        self.assertEqual(self.client.get('/tasks/?per_page=999999').context['page'].paginator.per_page,20)
    def test_filters_all_columns_and_sort_whitelist(self):
        self.task.notes_to_colleague='Please review proposal';self.task.start_date=date(2026,11,1);self.task.due_date=date(2026,11,30);self.task.save()
        self.login()
        queries=[f'no={self.task.pk}',f'sales={self.sales.pk}',f'engineer={self.engineer.pk}','start_from=2026-11-01&end_to=2026-11-30','progress_min=0&progress_max=10','notes=proposal','project_name=Test&task_name=Test','sort=-priority','sort=__malicious_column']
        for query in queries:
            with self.subTest(query=query):self.assertContains(self.client.get('/tasks/?'+query),'Test task')
        self.assertEqual(self.client.get('/tasks/?progress_max=999').context['page'].paginator.count,0)
    def test_dashboard_primary_workload(self):
        self.login();response=self.client.get('/dashboard/')
        self.assertEqual(response.context['sales_rows'][0]['stats']['total'],1)
        self.assertEqual(response.context['engineer_rows'][0]['stats']['total'],1)
    def test_preview_does_not_create_tasks(self):
        batch=self.batch([self.row()]);before=Task.objects.count()
        rows=preview_rows(batch,self.manager)
        self.assertEqual(rows[0]['state'],'new');self.assertEqual(Task.objects.count(),before)
        self.assertEqual(rows[0]['data']['start_date'],'2026-11-01')
        self.assertEqual(rows[0]['data']['due_date'],'2026-11-15')
    def test_import_assignments_status_progress_and_history(self):
        batch=self.batch([self.row(status='To Do',progress=100)])
        count,rows,done=commit_batch(batch,self.manager)
        self.assertEqual(count,1);self.assertTrue(done)
        task=Task.objects.get(title='New imported task')
        self.assertEqual(task.sales,self.sales);self.assertEqual(task.engineer,self.engineer)
        self.assertEqual(task.status,'todo');self.assertEqual(task.progress,100)
        self.assertEqual(task.notes_to_colleague,'Test message, not company data')
        self.assertTrue(Activity.objects.filter(task=task,summary__contains='นำเข้าจาก Excel').exists())
    def test_import_duplicate_file_and_reconfirm(self):
        batch=self.batch([self.row(),self.row()]);count,rows,done=commit_batch(batch,self.manager)
        self.assertEqual(count,1);self.assertEqual(rows[1]['state'],'duplicate')
        with self.assertRaises(ValidationError):commit_batch(batch,self.manager)
        new=self.batch([self.row()]);self.assertEqual(commit_batch(new,self.manager)[0],0)
    def test_import_errors_block_until_explicit_partial_confirmation(self):
        batch=self.batch([self.row(),self.row(title='Bad row',due_date='not a date')])
        count,rows,done=commit_batch(batch,self.manager)
        self.assertEqual(count,0);self.assertFalse(done);self.assertFalse(Task.objects.filter(title='New imported task').exists())
        count,rows,done=commit_batch(batch,self.manager,allow_partial=True)
        self.assertEqual(count,1);self.assertTrue(done)
    def test_invalid_user_and_duplicate_name_require_mapping(self):
        User.objects.create_user('second-sales',first_name='Sales',last_name='Tester',role='sales',team=self.team)
        batch=self.batch([self.row(sales='Sales Tester')])
        self.assertEqual(preview_rows(batch,self.manager)[0]['state'],'error')
        batch.options={'people':{person_key('sales','Sales Tester'):str(self.sales.pk)}}
        self.assertEqual(preview_rows(batch,self.manager)[0]['state'],'new')
    def test_import_mapping_cannot_inject_wrong_role(self):
        batch=self.batch([self.row(sales='Unknown')],people={person_key('sales','Unknown'):str(self.engineer.pk)})
        self.assertEqual(preview_rows(batch,self.manager)[0]['state'],'error')
    def test_import_formulas_rejected_without_execution(self):
        batch=self.batch([self.row(title='=1+1')])
        rows=preview_rows(batch,self.manager);self.assertEqual(rows[0]['state'],'error')
        self.assertIn('สูตร',' '.join(rows[0]['errors']))
    def test_import_dates_serial_percent_and_invalid_progress(self):
        book=Workbook();sheet=book.active;sheet.append([label for key,label in COLUMNS]);sheet.append(self.row(start_date=date(2026,11,1),due_date=46341,progress=0.75));sheet['H2'].number_format='0%'
        output=io.BytesIO();book.save(output)
        payload=read_xlsx(SimpleUploadedFile('test.xlsx',output.getvalue()))
        batch=ImportBatch(owner=self.manager,filename='test.xlsx',payload=payload,mapping=initial_mapping(payload),options={})
        rows=preview_rows(batch,self.manager);self.assertEqual(rows[0]['data']['progress'],75)
        self.assertEqual(rows[0]['data']['start_date'],'2026-11-01')
        bad=self.batch([self.row(progress=0.75)]);self.assertEqual(preview_rows(bad,self.manager)[0]['state'],'error')
    def test_new_project_requires_explicit_permission(self):
        batch=self.batch([self.row(project='Explicit new project')])
        self.assertEqual(preview_rows(batch,self.manager)[0]['state'],'error')
        batch.options={'create_projects':True,'new_category':'network'};batch.save()
        self.assertEqual(commit_batch(batch,self.manager)[0],1)
        project=Project.objects.get(title='Explicit new project')
        self.assertEqual(project.customer,'');self.assertEqual(project.category,'network')
        self.assertTrue(project.members.filter(pk=self.sales.pk).exists())
    def test_column_mapping_with_nonstandard_headers(self):
        payload=read_xlsx(self.excel([['Custom task','Test project','engineer']],headers=['Job','Site','Tech']))
        batch=ImportBatch(owner=self.manager,payload=payload,mapping={'title':'0','project':'1','engineer':'2'},options={})
        rows=preview_rows(batch,self.manager);self.assertEqual(rows[0]['state'],'new');self.assertEqual(rows[0]['data']['engineer'],self.engineer.pk)
    def test_fill_down_is_explicit(self):
        batch=self.batch([self.row(title='First'),self.row(title='Second',project='')])
        self.assertEqual(preview_rows(batch,self.manager)[1]['data']['project'],'')
        batch.options={'fill_project':True}
        self.assertEqual(preview_rows(batch,self.manager)[1]['data']['project'],self.project.pk)
    def test_import_http_upload_map_preview_confirm(self):
        self.login()
        response=self.client.post('/excel/import/',{'file':self.excel([self.row()]),'header_row':1})
        self.assertEqual(response.status_code,302)
        batch=ImportBatch.objects.latest('created_at')
        url=f'/excel/import/{batch.pk}/'
        self.assertEqual(self.client.get(url).status_code,200)
        mapping={f'col_{key}':str(i) for i,(key,label) in enumerate(COLUMNS)}
        response=self.client.post(url,{'action':'preview','revision':batch.revision,'new_category':'solution',**mapping})
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'พร้อมนำเข้า')
        self.assertFalse(Task.objects.filter(title='New imported task').exists())
        batch.refresh_from_db()
        response=self.client.post(url,{'action':'confirm','revision':batch.revision})
        self.assertEqual(response.status_code,302);self.assertTrue(Task.objects.filter(title='New imported task').exists())
    def test_import_batch_is_private(self):
        batch=self.batch([self.row()]);self.login(self.admin)
        self.assertEqual(self.client.get(f'/excel/import/{batch.pk}/').status_code,404)
        self.assertEqual(self.client.post(f'/excel/import/{batch.pk}/',{'action':'confirm'}).status_code,404)
    def test_import_error_download_and_expired_batch(self):
        batch=self.batch([self.row(progress=150)]);batch.preview=preview_rows(batch,self.manager);batch.save()
        self.login();response=self.client.get(f'/excel/import/{batch.pk}/errors/')
        self.assertContains(response,'Source Row');self.assertContains(response,'% Complete')
        ImportBatch.objects.filter(pk=batch.pk).update(created_at=timezone.now()-timedelta(days=2))
        self.assertEqual(self.client.get(f'/excel/import/{batch.pk}/').status_code,404)
    def test_export_eleven_columns_roundtrip_duplicate(self):
        self.login();response=self.client.get('/reports/?export=xlsx')
        book=load_workbook(io.BytesIO(response.content))
        self.assertEqual([c.value for c in book.active[1]],[label for key,label in COLUMNS])
        self.assertEqual(book.active['I2'].value,'sales');self.assertEqual(book.active['J2'].value,'engineer')
        payload=read_xlsx(SimpleUploadedFile('export.xlsx',response.content))
        batch=ImportBatch(owner=self.manager,payload=payload,mapping=initial_mapping(payload),options={})
        self.assertEqual(preview_rows(batch,self.manager)[0]['state'],'duplicate')
    def test_template_contains_no_mock_company_rows(self):
        self.login();response=self.client.get('/excel/template/')
        book=load_workbook(io.BytesIO(response.content));self.assertEqual(book['Tasks'].max_row,1)
        self.assertEqual(len(book['Tasks'].data_validations.dataValidation),3)
    def test_invalid_file_rejected(self):
        with self.assertRaises(ValidationError):read_xlsx(SimpleUploadedFile('bad.xlsx',b'not a zip'))
        with self.assertRaises(ValidationError):read_xlsx(SimpleUploadedFile('bad.xlsm',b'not a zip'))

    def test_stale_delete_does_not_remove_updated_task(self):
        self.inline('progress',20)
        response=self.client.post(f'/tasks/{self.task.pk}/delete/',{'version':1})
        self.assertEqual(response.status_code,409)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_import_row_limit_rejects_file_instead_of_truncating(self):
        with patch('work.excel.MAX_ROWS',2),self.assertRaises(ValidationError):
            read_xlsx(self.excel([self.row(title='One'),self.row(title='Two'),self.row(title='Three')]))

    def test_import_no_requires_positive_integer(self):
        batch=self.batch([self.row(no='not-an-id')])
        self.assertEqual(preview_rows(batch,self.manager)[0]['state'],'error')

    def test_stale_import_preview_cannot_be_confirmed(self):
        batch=self.batch([self.row()])
        ImportBatch.objects.filter(pk=batch.pk).update(revision=2)
        with self.assertRaises(ValidationError):commit_batch(batch,self.manager,expected_revision=1)
        self.assertFalse(Task.objects.filter(title='New imported task').exists())

    def test_deactivated_existing_assignee_does_not_block_other_worker_updates(self):
        self.sales.is_active=False;self.sales.save()
        response=self.inline('notes_to_colleague','Keep working',user=self.engineer)
        self.assertEqual(response.status_code,200)

@override_settings(DEBUG=True,ALLOW_LOCAL_LOGIN=True)
class ConcurrentUpdates(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_two_simultaneous_edits_only_one_wins(self):
        user=User.objects.create_user('concurrency',role='admin')
        task=Task.objects.create(title='Concurrent task',creator=user)
        barrier=threading.Barrier(2)
        def update(value):
            try:
                actor=User.objects.get(pk=user.pk);barrier.wait(timeout=10)
                try:
                    save_work(actor,{'title':task.title,'priority':'normal','status':'progress','progress':value,'version':1},pk=task.pk)
                    return 'saved'
                except EditConflict:return 'conflict'
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(update,[30,70]))
        self.assertEqual(sorted(results),['conflict','saved'])
        task.refresh_from_db();self.assertEqual(task.version,2);self.assertIn(task.progress,[30,70])

TENANT='11111111-2222-4333-8444-555555555555'
@override_settings(DEBUG=False,ALLOW_LOCAL_LOGIN=True,SECURE_SSL_REDIRECT=False,MICROSOFT_SSO_READY=True,MICROSOFT_TENANT_ID=TENANT)
class SSOTests(TestCase):
    def social(self,**claims):
        data={'tid':TENANT,'iss':f'https://login.microsoftonline.com/{TENANT}/v2.0','preferred_username':'testemployee@askme.co.th','sub':'test-subject','oid':'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'}
        data.update(claims)
        return SocialLogin(user=User(username='test-sso'),account=SocialAccount(provider='microsoft',uid='aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee',extra_data={'id_token':data}))
    def request(self):
        request=RequestFactory().get('/');request.user=AnonymousUser();return request
    def test_accepts_company_tenant_and_domain(self):
        login=self.social();CorporateSocialAdapter().pre_social_login(self.request(),login)
        self.assertEqual(login.user.email,'testemployee@askme.co.th');self.assertTrue(login.email_addresses[0].verified)
    def test_rejects_wrong_tenant_domain_issuer_or_guest(self):
        cases=[{'tid':'different'},{'preferred_username':'person@gmail.com'},{'preferred_username':'person@askme.co.th.evil.example'},{'iss':'https://evil.example/'},{'acct':1},{'idp':'live.com'}]
        for claims in cases:
            with self.subTest(claims=claims),self.assertRaises(ImmediateHttpResponse):CorporateSocialAdapter().pre_social_login(self.request(),self.social(**claims))
    def test_rejects_inactive_existing_account(self):
        User.objects.create_user('disabled',email='testemployee@askme.co.th',is_active=False)
        with self.assertRaises(ImmediateHttpResponse):CorporateSocialAdapter().pre_social_login(self.request(),self.social())
    def test_sso_not_configured_fails_closed(self):
        with override_settings(MICROSOFT_SSO_READY=False),self.assertRaises(ImmediateHttpResponse):CorporateSocialAdapter().pre_social_login(self.request(),self.social())
    def test_password_login_disabled_in_production_even_when_flag_true(self):
        User.objects.create_user('password-user',password='Strong-test-password!',email='password@askme.co.th')
        response=self.client.post('/login/',{'username':'password-user','password':'Strong-test-password!'})
        self.assertEqual(response.status_code,403);self.assertNotIn('_auth_user_id',self.client.session)
    def test_domain_enforced_for_user_creation(self):
        from .forms import CreateUserForm
        form=CreateUserForm({'username':'external','email':'external@gmail.com','role':'engineer','is_active':'on'})
        self.assertFalse(form.is_valid());self.assertIn('email',form.errors)
    def test_callback_cannot_create_session_without_oauth_state(self):
        response=self.client.get('/accounts/oidc/microsoft/login/callback/?code=forged&state=forged')
        self.assertIn(response.status_code,[200,404]);self.assertNotIn('_auth_user_id',self.client.session)

    def test_microsoft_redirect_uses_company_tenant_state_and_pkce(self):
        from urllib.parse import urlparse,parse_qs
        config={'openid_connect':{'APPS':[{'provider_id':'microsoft','name':'Microsoft 365','client_id':'test-client-id','secret':'test-secret-not-a-real-credential','settings':{'server_url':f'https://login.microsoftonline.com/{TENANT}/v2.0','fetch_userinfo':False,'token_auth_method':'client_secret_post','oauth_pkce_enabled':True,'uid_field':'oid'}}]}}
        metadata={'authorization_endpoint':f'https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/authorize','token_endpoint':f'https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token','issuer':f'https://login.microsoftonline.com/{TENANT}/v2.0','jwks_uri':f'https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys'}
        with override_settings(SOCIALACCOUNT_PROVIDERS=config),patch('requests.sessions.Session.get') as get:
            get.return_value.json.return_value=metadata
            response=self.client.post('/accounts/oidc/microsoft/login/')
        self.assertEqual(response.status_code,302)
        url=urlparse(response.url);params=parse_qs(url.query)
        self.assertEqual(url.netloc,'login.microsoftonline.com');self.assertIn(TENANT,url.path)
        self.assertEqual(params['response_type'],['code']);self.assertEqual(params['code_challenge_method'],['S256'])
        self.assertTrue(params['state'][0]);self.assertTrue(params['code_challenge'][0])
        self.assertIn('/accounts/oidc/microsoft/login/callback/',params['redirect_uri'][0])
