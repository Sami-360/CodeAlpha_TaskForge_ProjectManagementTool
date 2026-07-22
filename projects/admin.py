from django.contrib import admin

from django.db.models import Count

from projects.models import Project, ProjectActivity, ProjectLabel, ProjectMember


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0
    readonly_fields = ['joined_at']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'member_count', 'created_at', 'updated_at']
    search_fields = ['name', 'owner__username', 'owner__email']
    list_filter = ['owner', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ProjectMemberInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_member_count=Count('memberships'))

    @admin.display(ordering='_member_count', description='Members')
    def member_count(self, project):
        return project._member_count


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ['project', 'user', 'role', 'added_by', 'joined_at']
    search_fields = ['project__name', 'user__username', 'user__email']
    list_filter = ['role', 'project', 'joined_at']
    readonly_fields = ['joined_at']


@admin.register(ProjectLabel)
class ProjectLabelAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'color', 'created_by', 'created_at']
    search_fields = ['name', 'project__name']
    list_filter = ['project', 'created_at']
    readonly_fields = ['created_at']


@admin.register(ProjectActivity)
class ProjectActivityAdmin(admin.ModelAdmin):
    list_display = ['project', 'action', 'actor', 'task', 'target_user', 'created_at']
    search_fields = ['project__name', 'actor__username', 'task__title']
    list_filter = ['action', 'project', 'created_at']
    readonly_fields = ['project', 'action', 'actor', 'task', 'target_user', 'metadata', 'created_at']
