from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('members/', views.members, name='members'),
    path('upload-zip/', views.upload_zip, name='upload_zip'),
    path('compare/', views.compare_images, name='compare_images'),
    path('process_duplicates/', views.process_selected_duplicates, name='process_selected_duplicates'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)