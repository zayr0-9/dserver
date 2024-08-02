from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.file_upload, name='file_upload'),
    path('files/<path:path>/', views.file_list, name='file_list'),
    path('files/', views.file_list, name='file_list'),
    path('download/<path:path>/<str:filename>/',
         views.download_file, name='download_file'),
    path('download/<str:filename>/', views.download_file,
         {'path': ''}, name='download_file_root'),
]
