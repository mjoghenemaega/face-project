# accounts/urls.py
from django.urls import path
from . import views
from attendance.views import teacher_login, teacher_dashboard,teacher_signup
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path('enroll', views.EnrollUserView.as_view(), name='enroll-user'),
    path("enroll-page/", views.student_enroll_page, name="student_enroll_page"),
    path('teacher/login/', teacher_login, name='login'),
    path('teacher/dashboard/', teacher_dashboard, name='teacher_dashboard'),
    path('teacher/signup/', teacher_signup, name='teacher_signup'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]