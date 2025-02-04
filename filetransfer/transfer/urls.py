from django.urls import path, re_path, include
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('api/', include('transfer.api_urls')),
    path('download/<path:path>/<str:filename>/',
         views.download_file, name='download_file'),
    path('download/<str:filename>/', views.download_file,
         {'path': ''}, name='download_file_root'),
    # Search files
    path('search/', views.search_files, name='search_files'),
    # Download zipped folder
    path('download_zip/', views.download_zip, name='download_zip'),
    # Admin
    path('serveradmin/', views.admin_pin_entry,
         name='admin_pin_entry'),  # Admin PIN entry
    path('serveradmin/categories/', views.category_list, name='category_list'),
    path('serveradmin/categories/create/',
         views.category_create, name='category_create'),
    path('serveradmin/categories/edit/<int:pk>/',
         views.category_edit, name='category_edit'),
    path('serveradmin/categories/delete/<int:pk>/',
         views.category_delete, name='category_delete'),
    path('serveradmin-console/', views.admin_console,
         name='adminconsole'),  # Admin console
    path('toggle-visibility/', views.toggle_visibility, name='toggle_visibility'),
    path('accounts/', include('django.contrib.auth.urls')),
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html'),
            name='homepage'),
]
