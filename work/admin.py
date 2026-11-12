from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Team, Project, Task, Comment, Attachment, Activity

@admin.register(User)
class WorkUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('งานและทีม', {'fields': ('role', 'team')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('งานและทีม', {'fields': ('role', 'team')}),)
    list_display = ['username', 'first_name', 'role', 'team', 'is_active']

admin.site.register(Team)
@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'actor', 'summary']
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
