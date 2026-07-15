from django.contrib import admin

from projects.models import Project, ProjectMember


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0
    readonly_fields = ['joined_at']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'created_at', 'updated_at']
    search_fields = ['name', 'owner__username', 'owner__email']
    list_filter = ['created_at']
    inlines = [ProjectMemberInline]


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ['project', 'user', 'role', 'added_by', 'joined_at']
    search_fields = ['project__name', 'user__username', 'user__email']
    list_filter = ['role', 'joined_at']
