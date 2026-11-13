from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path, include
from work import views, import_views
from work.auth import ThrottledLoginView

urlpatterns = [
    path('accounts/', include('allauth.urls')),
    path('excel/import/', import_views.import_upload, name='import_upload'),
    path('excel/import/<uuid:pk>/', import_views.import_preview, name='import_preview'),
    path('excel/import/<uuid:pk>/errors/', import_views.import_errors, name='import_errors'),
    path('excel/template/', import_views.excel_template, name='excel_template'),
    path('admin/', admin.site.urls),
    path('login/', ThrottledLoginView.as_view(), name='login'),
    path('logout/', auth.LogoutView.as_view(), name='logout'),
    path('password/', auth.PasswordChangeView.as_view(template_name='work/form.html', extra_context={'title': 'เปลี่ยนรหัสผ่าน'}, success_url='/'), name='password_change'),
    path('', views.task_list, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('tasks/<int:pk>/inline/', views.task_inline, name='task_inline'),
    path('tasks/grid/', views.task_grid, name='task_grid'),
    path('projects/', views.project_list, name='projects'),
    path('projects/new/', views.project_form, name='project_create'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_form, name='project_edit'),
    path('projects/<int:pk>/delete/', views.delete_object, {'kind': 'project'}, name='project_delete'),
    path('projects/<int:pk>/upload/', views.upload, {'kind': 'project'}, name='project_upload'),
    path('tasks/', views.task_list, name='tasks'),
    path('tasks/new/', views.task_form, name='task_create'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/edit/', views.task_form, name='task_edit'),
    path('tasks/<int:pk>/delete/', views.delete_object, {'kind': 'task'}, name='task_delete'),
    path('tasks/<int:pk>/comments/', views.add_comment, name='comment_create'),
    path('tasks/<int:pk>/upload/', views.upload, {'kind': 'task'}, name='task_upload'),
    path('attachments/<int:pk>/', views.download, name='download'),
    path('team/', views.team_view, name='team'),
    path('activity/', views.activity_view, name='activity'),
    path('reports/', views.reports, name='reports'),
    path('users/', views.users, name='users'),
    path('users/new/', views.user_form, name='user_create'),
    path('users/<int:pk>/edit/', views.user_form, name='user_edit'),
    path('users/<int:pk>/password/', views.reset_password, name='user_password'),
    path('teams/new/', views.team_create, name='team_create'),
]
