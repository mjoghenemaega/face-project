from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, TeacherStudent

class TeacherStudentInline(admin.TabularInline):
    model = TeacherStudent
    fk_name = 'teacher'
    extra = 1

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role')
    list_filter = ('role',)
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'rfid_uid', 'face_hash', 'face_image')}),
    )
    inlines = []

    def get_inlines(self, request, obj=None):
        if obj and obj.role == 'teacher':
            return [TeacherStudentInline]
        return []

class TeacherStudentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'student', 'assigned_date')
    list_filter = ('teacher', 'assigned_date')
    search_fields = ('teacher__username', 'student__username')
    autocomplete_fields = ['teacher', 'student']

admin.site.register(User, CustomUserAdmin)
admin.site.register(TeacherStudent, TeacherStudentAdmin)