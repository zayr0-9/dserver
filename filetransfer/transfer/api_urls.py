from django.urls import path
from . import views

urlpatterns = [
    path('drives/', views.get_drives_api, name='get_drives_api'),
    path('drive/<str:drive_letter>/files/',
         views.file_list_api, name='file_list_api'),
    path('drive/<str:drive_letter>/validate_pin/',
         views.validate_pin_api, name='validate_pin_api'),

]
