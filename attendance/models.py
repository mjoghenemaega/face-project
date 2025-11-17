from django.db import models
from django.conf import settings
from django.utils import timezone
from cloudinary.models import CloudinaryField

class AttendanceRecord(models.Model):
    ATTENDANCE_TYPE = [
        ('IN', 'Class In'),
        ('OUT', 'Class Out'),
    ]
    
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    rfid_uid = models.CharField(max_length=128)
    image = CloudinaryField('image', folder='attendance/')
    match_confidence = models.FloatField()  # percentage 0..100
    granted = models.BooleanField(default=False)
    attendance_type = models.CharField(max_length=3, choices=ATTENDANCE_TYPE, default='IN')

    class Meta:
        ordering = ['-timestamp']
        # Ensure one in and one out per student per day
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'attendance_type'],
                condition=models.Q(timestamp__date=timezone.now().date()),
                name='unique_daily_attendance_type'
            )
        ]

    def __str__(self):
        return f"{self.student} {self.attendance_type} @ {self.timestamp} - {'OK' if self.granted else 'DENIED'}"

    @property
    def is_late(self):
        if self.attendance_type == 'IN':
            time = self.timestamp.time()
            return time.hour > 8 or (time.hour == 8 and time.minute > 0)
        return False

    @property
    def is_early_departure(self):
        if self.attendance_type == 'OUT':
            time = self.timestamp.time()
            return time.hour < 16
        return False