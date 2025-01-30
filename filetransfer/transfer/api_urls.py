from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.api_login, name='api_login'),
    path('auth/logout/', views.api_logout, name='api_logout'),
    path('auth/csrf/', views.get_csrf_token, name='get_csrf_token'),
    path('drives/', views.get_drives_api, name='get_drives_api'),
    path('drive/<str:drive_letter>/files/',
         views.file_list_api, name='file_list_api'),
    path('drive/<str:drive_letter>/validate_pin/',
         views.validate_pin_api, name='validate_pin_api'),
    #     path('api/upload/', views.file_upload, name='file_upload_api'),
    path('upload/<str:base_dir>/', views.file_upload,
         {'relative_path': ''}, name='file_upload_api_root'),
    path('upload/<str:base_dir>/<path:relative_path>/',
         views.file_upload, name='file_upload_api'),
    path('delete/', views.delete_item, name='delete_item_api'),
    path('files/content/', views.get_file_content, name='get_file_content'),
    path('files/save/', views.save_file_content, name='save_file_content'),
    path('stream/<str:drive_letter>/<path:path>/',
         views.stream_hls, name='stream_hls'),
    path('search/', views.search_files, name='search_files'),
    path('admin/console/', views.admin_console_api, name='admin_console_api'),
    path("update-drive-letter/", views.update_drive_letter,
         name="update_drive_letter"),
    path("convert-for-stream/", views.convert_for_stream, name="convert_for_stream")

]
