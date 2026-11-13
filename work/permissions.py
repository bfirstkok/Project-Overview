from django.db.models import Q
from .models import Project, Task, Activity, User

def personal_scope(user):
    return Q(creator=user) | Q(sales=user) | Q(engineer=user) | Q(assignees=user) | Q(project__owner=user) | Q(project__members=user)

def team_task_scope(user):
    own = personal_scope(user)
    if not user.team_id: return own
    return own | Q(creator__team_id=user.team_id) | Q(sales__team_id=user.team_id) | Q(engineer__team_id=user.team_id) | Q(assignees__team_id=user.team_id) | Q(project__owner__team_id=user.team_id) | Q(project__members__team_id=user.team_id)

def tasks_for(user):
    qs = Task.objects.select_related('project', 'creator', 'sales', 'engineer').prefetch_related('assignees')
    if user.is_admin: return qs
    return qs.filter(team_task_scope(user) if user.is_manager else personal_scope(user)).distinct()

def projects_for(user):
    qs = Project.objects.select_related('owner').prefetch_related('members')
    if user.is_admin: return qs
    scope = Q(owner=user) | Q(members=user) | Q(tasks__sales=user) | Q(tasks__engineer=user) | Q(tasks__assignees=user)
    if user.is_manager and user.team_id:
        scope |= Q(owner__team_id=user.team_id) | Q(members__team_id=user.team_id) | Q(tasks__in=tasks_for(user))
    return qs.filter(scope).distinct()

def edit_project(user, project):
    return user.is_admin or project.owner_id == user.pk or (user.is_manager and projects_for(user).filter(pk=project.pk).exists())

def manage_task(user, task):
    return user.is_admin or task.creator_id == user.pk or (user.is_manager and tasks_for(user).filter(pk=task.pk).exists())

def edit_task(user, task):
    return manage_task(user, task) or user.pk in [task.sales_id, task.engineer_id] or task.assignees.filter(pk=user.pk).exists()

def assignable_users(user):
    qs = User.objects.filter(is_active=True, is_service_account=False)
    if user.is_admin: return qs
    if user.is_manager: return qs.filter(Q(pk=user.pk) | (Q(team_id=user.team_id) if user.team_id else Q(pk=user.pk)))
    return qs.filter(Q(pk=user.pk) | Q(team_id=user.team_id) | Q(projects__in=projects_for(user)) | Q(owned_projects__in=projects_for(user))).distinct()
def activities_for(user):
    qs = Activity.objects.select_related('actor', 'task', 'project')
    return qs if user.is_admin else qs.filter(Q(task__in=tasks_for(user)) | Q(project__in=projects_for(user)) | Q(actor=user)).distinct()
