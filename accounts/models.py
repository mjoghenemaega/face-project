# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
import numpy as np


class User(AbstractUser):
    ROLE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    rfid_uid = models.CharField(max_length=128, blank=True, null=True, unique=True)
    # store pHash hex string for lightweight matching
    face_hash = models.CharField(max_length=128, blank=True, null=True)
    # optional: store the face image (base64 or imagefield)
    face_image = models.ImageField(upload_to='faces/', blank=True, null=True)
    face_features = models.BinaryField(null=True, blank=True)


       
    
    def save_face_features(self, features):
        """Save face features as binary data"""
        self.face_features = features.tobytes()
        
    def get_face_features(self):
        """Get face features as numpy array"""
        if self.face_features:
            return np.frombuffer(self.face_features, dtype=np.float64)
        return None
        
    def __str__(self):
        return f"{self.username} ({self.role})"
    




# ...existing code...

class TeacherStudent(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teacher_assignments')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_assignments')
    assigned_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['teacher', 'student']

    def __str__(self):
        return f"{self.teacher.username} -> {self.student.username}"