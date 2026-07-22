"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve as serve_media

from config.views import health_check
from projects.views import DashboardView, GlobalSearchView, ProjectLabelDetailView

admin.site.site_header = 'TaskForge Administration'
admin.site.site_title = 'TaskForge Admin'
admin.site.index_title = 'Project Management Control Panel'

urlpatterns = [
    path('', RedirectView.as_view(url='/static/pages/login.html', permanent=False), name='frontend-home'),
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='api-health'),
    path('api/auth/', include('accounts.urls')),
    path('api/projects/', include('projects.urls')),
    path('api/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('api/search/', GlobalSearchView.as_view(), name='global-search'),
    path('api/project-labels/<int:pk>/', ProjectLabelDetailView.as_view(), name='project-label-detail'),
    path('api/', include('tasks.urls')),
    path('api/', include('comments.urls')),
    path('api/notifications/', include('notifications.urls')),
]

if settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve_media, {'document_root': settings.MEDIA_ROOT}),
    ]
