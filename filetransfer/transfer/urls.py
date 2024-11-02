from django.urls import path, re_path
from . import views

urlpatterns = [
    # Homepage (React serves the frontend)
    # React index.html for the frontend
    path('', views.homepage, name='homepage'),
    path('drive/', views.drives, name='drives'),
    # File upload and management
    path('upload/', views.file_upload, name='file_upload'),
    #     path('files/<path:path>/', views.file_list, name='file_list'),
    #     path('files/', views.file_list, name='file_list'),
    re_path(r'^files/(?P<base_dir>[^/]+)/(?P<path>.*)$',
            views.file_list, name='file_list'),
    path('download/<path:path>/<str:filename>/',
         views.download_file, name='download_file'),
    path('download/<str:filename>/', views.download_file,
         {'path': ''}, name='download_file_root'),

    # Video streaming
    path('video/<path:path>/<str:filename>/',
         views.video_stream_page, name='video_stream_page'),
    #     path('stream/<path:path>/<str:filename>/',
    #          views.stream_video, name='stream_video'), old for file mode
    # Video streaming endpoint
    #     path('stream/<int:id>/', views.stream_video_by_id,
    #          name='stream_video_by_id'),  # for react

    # Search files
    path('search/', views.search_files, name='search_files'),

    # Download zipped folder
    path('download_zip/', views.download_zip, name='download_zip'),

    # File mode
    path('file-mode/', views.file_mode, name='file_list'),

    # Theatre mode (React-based theatre)
    # React app will handle this
    path('theatre-mode/', views.index, name='theatre_mode'),

    # Admin
    path('serveradmin/', views.admin_pin_entry,
         name='admin_pin_entry'),  # Admin PIN entry
    path('serveradmin-console/', views.admin_console,
         name='adminconsole'),  # Admin console
    path('toggle-visibility/', views.toggle_visibility, name='toggle_visibility'),

    # API for video data (for React)
    path('api/videos/', views.video_list, name='video_list'),

    # Catch-all route for React (optional, if you use React Router for frontend routing)
    path('theatre/', views.index),  # Catch-all for React theatre mode
    # Serve the same index.html
    path('theatre-mode/<path:resource>', views.index),
    path('theatre-mode/', views.index, name='theatre_mode'),
]
