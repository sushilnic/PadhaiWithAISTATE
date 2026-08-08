"""
URL configuration for school_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.shortcuts import render
from django.views.static import serve as media_serve

urlpatterns = [
    # Django admin — moved off the default `/admin/` path so automated
    # bot scanners hitting /admin/ get a 404 instead of a real login form.
    path('pai_admin/', admin.site.urls),
    path('', include('school_app.urls')),
]

# Serve user-uploaded media (uploads/toppers etc.) via Django itself.
# Enabled whenever SERVE_MEDIA_LOCALLY is True (default: True unless explicitly
# set to False in production, where the webserver — IIS/nginx — should serve
# /media/ directly for better performance).
#
# NOTE: we use django.views.static.serve directly because Django's static()
# helper silently returns [] whenever DEBUG=False.
if getattr(settings, 'SERVE_MEDIA_LOCALLY', True):
    media_prefix = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += [
        re_path(rf'^{media_prefix}/(?P<path>.*)$', media_serve,
                {'document_root': settings.MEDIA_ROOT}),
    ]


# Custom error handlers
def custom_400(request, exception):
    return render(request, 'school_app/errors/404.html', status=400)

def custom_403(request, exception):
    return render(request, 'school_app/errors/403.html', status=403)

def custom_404(request, exception):
    return render(request, 'school_app/errors/404.html', status=404)

def custom_500(request):
    return render(request, 'school_app/errors/500.html', status=500)

handler400 = custom_400
handler403 = custom_403
handler404 = custom_404
handler500 = custom_500