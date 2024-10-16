from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),  # Homepage
    path('upload/', views.file_upload, name='file_upload'),
    path('files/<path:path>/', views.file_list, name='file_list'),
    path('files/', views.file_list, name='file_list'),
    path('download/<path:path>/<str:filename>/',
         views.download_file, name='download_file'),
    path('download/<str:filename>/', views.download_file,
         {'path': ''}, name='download_file_root'),
    #     path('thumbnails/<str:filename>/',
    #     views.serve_thumbnail, name='serve_thumbnail'),
    path('video/<path:path>/<str:filename>/',
         views.video_stream_page, name='video_stream_page'),
    path('stream/<path:path>/<str:filename>/',
         views.stream_video, name='stream_video'),
    path('search/', views.search_files, name='search_files'),  # Search files view
    path('download_zip/', views.download_zip, name='download_zip'),    path('',
                                                                            views.homepage, name='homepage'),  # Homepage
    # File mode redirects to file_list
    path('file-mode/', views.file_mode, name='file_list'),
    path('theatre-mode/', views.theatre_mode,
         name='theatre_mode'),  # Theatre mode
    path('serveradmin/', views.admin_pin_entry,
         name='admin_pin_entry'),  # Admin PIN entry
    path('serveradmin-console/', views.admin_console,
         name='adminconsole'),  # Admin console
    path('toggle-visibility/', views.toggle_visibility, name='toggle_visibility'),

]
