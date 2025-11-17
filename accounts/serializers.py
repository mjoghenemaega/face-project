# accounts/serializers.py
from rest_framework import serializers
from .models import User

class EnrollmentSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=('teacher','student'))
    rfid_uid = serializers.CharField()
    image_base64 = serializers.CharField()  # face to enroll
