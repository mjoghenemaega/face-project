# attendance/serializers.py
from rest_framework import serializers

class AttendanceUploadSerializer(serializers.Serializer):
    rfid_uid = serializers.CharField()
    image_base64 = serializers.CharField()  # accept data URL or raw base64
