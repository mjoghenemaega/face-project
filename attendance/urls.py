# attendance/urls.py
from django.urls import path
from .views import AttendanceUploadView,encode_image

urlpatterns = [
    path('upload', AttendanceUploadView.as_view(), name='attendance-upload'),
    path('encode-image', encode_image, name='encode-image'),
]
