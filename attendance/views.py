# attendance/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import AttendanceUploadSerializer
from accounts.models import User, TeacherStudent
from .models import AttendanceRecord
from .utils import base64_to_pil, detect_and_crop_face, compute_phash, phash_to_hex, compare_phash
from django.core.files.base import ContentFile
import base64
import io

# threshold specified by you (30%)
MIN_CONFIDENCE = 50.0

import io
from PIL import Image


from django.utils import timezone
from django.db import IntegrityError


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import AttendanceUploadSerializer
from accounts.models import User, TeacherStudent
from .models import AttendanceRecord
from .utils import base64_to_pil, detect_and_crop_face, compute_phash, phash_to_hex, compare_phash
from cloudinary.uploader import upload
import base64
import io
from PIL import Image
from django.utils import timezone
from django.db import IntegrityError

# threshold specified by you (30%)
MIN_CONFIDENCE = 50.0


class AttendanceUploadView(APIView):
    """
    POST (multipart/form-data):
    {
        "rfid_uid": "UID-STRING",
        "image": <uploaded file>
    }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        rfid_uid = request.data.get('rfid_uid')
        image_file = request.FILES.get('image')

        if not rfid_uid or not image_file:
            return Response(
                {"detail": "rfid_uid and image are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find user by RFID
        try:
            user = User.objects.get(rfid_uid=rfid_uid)

            # Determine if this is class IN or OUT
            today = timezone.now().date()
            existing_attendance = AttendanceRecord.objects.filter(
                student=user,
                timestamp__date=today,
                granted=True
            ).order_by('timestamp')

            # Determine attendance type
            attendance_type = 'IN'
            if existing_attendance.exists():
                last_record = existing_attendance.last()
                if last_record.attendance_type == 'IN':
                    attendance_type = 'OUT'
                elif last_record.attendance_type == 'OUT':
                    return Response({
                        "granted": False,
                        "message": "Already checked out for today"
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Convert uploaded image file to PIL
            try:
                pil_img = Image.open(image_file).convert("RGB")
            except Exception as e:
                return Response({"detail": "Invalid image file", "error": str(e)}, 
                              status=status.HTTP_400_BAD_REQUEST)

            # Detect and crop face
            cropped = detect_and_crop_face(pil_img)
            if cropped is None:
                return Response({"detail": "No face detected in uploaded image."}, 
                              status=status.HTTP_400_BAD_REQUEST)

            # Compute perceptual hash for uploaded face
            uploaded_phash = compute_phash(cropped)
            uploaded_hex = phash_to_hex(uploaded_phash)

            # Check if user has stored reference face hash
            if not user.face_hash:
                return Response({"detail": "User does not have enrolled face."}, 
                              status=status.HTTP_400_BAD_REQUEST)

            # Compare uploaded face with stored hash
            similarity = compare_phash(uploaded_hex, user.face_hash)
            granted = similarity >= MIN_CONFIDENCE

            if not granted:
                return Response({
                    "granted": False,
                    "match_confidence": similarity,
                    "message": "Face verification failed"
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Upload to Cloudinary
            cloudinary_url_str = None
            try:
                img_io = io.BytesIO()
                pil_img.save(img_io, format='JPEG')
                img_io.seek(0)
                
                upload_response = upload(
                    img_io,
                    folder='attendance/',
                    public_id=f"{user.username}_{rfid_uid}_{attendance_type}_{timezone.now().timestamp()}",
                    resource_type='image',
                    overwrite=False
                )
                
                cloudinary_url_str = upload_response['secure_url']
                
            except Exception as e:
                return Response({
                    "detail": "Failed to upload image to Cloudinary",
                    "error": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Save attendance record
            try:
                current_time = timezone.localtime()
                is_late = False
                is_early = False

                # Check if late arrival (after 8:00 AM)
                if attendance_type == 'IN':
                    is_late = current_time.hour > 8 or (current_time.hour == 8 and current_time.minute > 0)

                # Check if early departure (before 4:00 PM)
                if attendance_type == 'OUT':
                    is_early = current_time.hour < 16

                # Create attendance record with Cloudinary URL
                attendance = AttendanceRecord.objects.create(
                    student=user,
                    rfid_uid=rfid_uid,
                    image=cloudinary_url_str,  # Store Cloudinary URL
                    match_confidence=similarity,
                    granted=granted,
                    attendance_type=attendance_type
                )

                # Prepare response message
                message = f"{'Entry' if attendance_type == 'IN' else 'Exit'} recorded successfully"
                if is_late:
                    message += " (Late arrival)"
                if is_early:
                    message += " (Early departure)"

                return Response({
                    "granted": granted,
                    "match_confidence": similarity,
                    "attendance_type": attendance_type,
                    "timestamp": attendance.timestamp,
                    "is_late": is_late,
                    "is_early": is_early,
                    "image_url": cloudinary_url_str,
                    "message": message
                }, status=status.HTTP_200_OK)

            except IntegrityError:
                return Response({
                    "granted": False,
                    "message": f"Already recorded {attendance_type} attendance today"
                }, status=status.HTTP_400_BAD_REQUEST)

        except User.DoesNotExist:
            return Response({"detail": "RFID not registered."}, 
                          status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "detail": "An error occurred",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ...rest of your views (encode_image, teacher_dashboard, teacher_login, teacher_signup)...




# class AttendanceUploadView(APIView):
#     """
#     POST (multipart/form-data):
#     {
#         "rfid_uid": "UID-STRING",
#         "image": <uploaded file>
#     }
#     """
#     permission_classes = [permissions.AllowAny]

#     def post(self, request):
#         rfid_uid = request.data.get('rfid_uid')
#         image_file = request.FILES.get('image')

#         if not rfid_uid or not image_file:
#             return Response(
#                 {"detail": "rfid_uid and image are required."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # Find user by RFID
#         try:
#             user = User.objects.get(rfid_uid=rfid_uid)

#             # Determine if this is class IN or OUT
#             today = timezone.now().date()
#             existing_attendance = AttendanceRecord.objects.filter(
#                 student=user,
#                 timestamp__date=today,
#                 granted=True
#             ).order_by('timestamp')

#             # Determine attendance type
#             attendance_type = 'IN'
#             if existing_attendance.exists():
#                 last_record = existing_attendance.last()
#                 if last_record.attendance_type == 'IN':
#                     attendance_type = 'OUT'
#                 elif last_record.attendance_type == 'OUT':
#                     return Response({
#                         "granted": False,
#                         "message": "Already checked out for today"
#                     }, status=status.HTTP_400_BAD_REQUEST)

#             # Convert uploaded image file to PIL
#             try:
#                 pil_img = Image.open(image_file)
#             except Exception as e:
#                 return Response({"detail": "Invalid image file", "error": str(e)}, 
#                               status=status.HTTP_400_BAD_REQUEST)

#             # Detect and crop face
#             cropped = detect_and_crop_face(pil_img)
#             if cropped is None:
#                 return Response({"detail": "No face detected in uploaded image."}, 
#                               status=status.HTTP_400_BAD_REQUEST)

#             # Compute perceptual hash for uploaded face
#             uploaded_phash = compute_phash(cropped)
#             uploaded_hex = phash_to_hex(uploaded_phash)

#             # Check if user has stored reference face hash
#             if not user.face_hash:
#                 return Response({"detail": "User does not have enrolled face."}, 
#                               status=status.HTTP_400_BAD_REQUEST)

#             # Compare uploaded face with stored hash
#             similarity = compare_phash(uploaded_hex, user.face_hash)
#             granted = similarity >= MIN_CONFIDENCE

#             if not granted:
#                 return Response({
#                     "granted": False,
#                     "match_confidence": similarity,
#                     "message": "Face verification failed"
#                 }, status=status.HTTP_401_UNAUTHORIZED)

#             # Save attendance record
#             try:
#                 current_time = timezone.localtime()
#                 is_late = False
#                 is_early = False

#                 # Check if late arrival (after 8:00 AM)
#                 if attendance_type == 'IN':
#                     is_late = current_time.hour > 8 or (current_time.hour == 8 and current_time.minute > 0)

#                 # Check if early departure (before 4:00 PM)
#                 if attendance_type == 'OUT':
#                     is_early = current_time.hour < 16

#                 # Save image
#                 img_io = io.BytesIO()
#                 pil_img.save(img_io, format='JPEG')
#                 img_content = ContentFile(img_io.getvalue(), 
#                                         name=f"{user.username}_{rfid_uid}_{attendance_type}.jpg")

#                 attendance = AttendanceRecord.objects.create(
#                     student=user,
#                     rfid_uid=rfid_uid,
#                     image=img_content,
#                     match_confidence=similarity,
#                     granted=granted,
#                     attendance_type=attendance_type
#                 )

#                 # Prepare response message
#                 message = f"{'Entry' if attendance_type == 'IN' else 'Exit'} recorded successfully"
#                 if is_late:
#                     message += " (Late arrival)"
#                 if is_early:
#                     message += " (Early departure)"

#                 return Response({
#                     "granted": granted,
#                     "match_confidence": similarity,
#                     "attendance_type": attendance_type,
#                     "timestamp": attendance.timestamp,
#                     "is_late": is_late,
#                     "is_early": is_early,
#                     "message": message
#                 }, status=status.HTTP_200_OK)

#             except IntegrityError:
#                 return Response({
#                     "granted": False,
#                     "message": f"Already recorded {attendance_type} attendance today"
#                 }, status=status.HTTP_400_BAD_REQUEST)

#         except User.DoesNotExist:
#             return Response({"detail": "RFID not registered."}, 
#                           status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             return Response({
#                 "detail": "An error occurred",
#                 "error": str(e)
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


import base64
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt  # Only for testing with Postman; remove in production
def encode_image(request):
    """
    POST endpoint that receives an image file and returns its base64 string.
    """
    if request.method == "POST":
        image_file = request.FILES.get('image')
        if not image_file:
            return JsonResponse({'error': 'No image file provided'}, status=400)

        # Read image data
        image_data = image_file.read()

        # Convert to Base64
        encoded_string = base64.b64encode(image_data).decode('utf-8')

        return JsonResponse({
            'filename': image_file.name,
            'base64_string': encoded_string
        })
    else:
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)




from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta

#@login_required
# def teacher_dashboard(request):
#     if request.user.role != 'teacher':
#         return redirect('login')
    
#     # Get teacher's students
#     teacher_students = TeacherStudent.objects.filter(teacher=request.user).select_related('student')
#     students = [ts.student for ts in teacher_students]
#     total_students = len(students)

#         # Get date filter
#     selected_date = request.GET.get('date', timezone.now().date().isoformat())
#     try:
#         filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
#     except ValueError:
#         filter_date = timezone.now().date()
    
#     # Get attendance stats
#     today = timezone.now().date()
#     attendance_data = AttendanceRecord.objects.filter(
#         student__in=students,
#         timestamp__date=today
#     ).select_related('student')

#     # Calculate attendance statistics
#     student_stats = []
#     for student in students:
#         today_attendance = attendance_data.filter(student=student)
#         class_in = today_attendance.filter(attendance_type='IN').first()
#         class_out = today_attendance.filter(attendance_type='OUT').first()
        
#         total_days = AttendanceRecord.objects.filter(
#             student=student, 
#             attendance_type='IN',
#             granted=True
#         ).count()
        
#         student_stats.append({
#             'student': student,
#             'today_attendance': class_in is not None and class_in.granted,
#             'total_attendance': total_days,
#             'attendance_percentage': (total_days / total_students * 100) if total_students > 0 else 0,
#             'class_in_time': class_in.timestamp.strftime('%H:%M %p') if class_in else None,
#             'class_out_time': class_out.timestamp.strftime('%H:%M %p') if class_out else None,
#             'is_late': class_in.is_late if class_in else False,
#             'left_early': class_out.is_early_departure if class_out else False
#         })

#     context = {
#         'student_stats': student_stats,
#         'total_students': len(students),
#         'present_today': sum(1 for stat in student_stats if stat['today_attendance']),
#         'today': filter_date,
#         'date_filter': selected_date
#     }
    
#     return render(request, 'accounts/teacher_dashboard.html', context)


@login_required
def teacher_dashboard(request):
    if request.user.role != 'teacher':
        return redirect('login')
    
    # Get teacher's students
    teacher_students = TeacherStudent.objects.filter(teacher=request.user).select_related('student')
    students = [ts.student for ts in teacher_students]
    total_students = len(students)

    # Get date filter from query parameter
    selected_date = request.GET.get('date')
    try:
        if selected_date:
            filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        else:
            filter_date = timezone.now().date()
    except ValueError:
        filter_date = timezone.now().date()
    
    # Get attendance records for the selected date
    attendance_data = AttendanceRecord.objects.filter(
        student__in=students,
        timestamp__date=filter_date,
        granted=True
    ).select_related('student')

    # Calculate attendance statistics
    student_stats = []
    for student in students:
        # Get attendance records for this student on the selected date
        student_attendance_today = attendance_data.filter(student=student)
        class_in = student_attendance_today.filter(attendance_type='IN').first()
        class_out = student_attendance_today.filter(attendance_type='OUT').first()
        
        # Calculate overall attendance percentage (all-time)
        # Count all unique dates where student checked IN and was granted
        student_in_records = AttendanceRecord.objects.filter(
            student=student, 
            attendance_type='IN',
            granted=True
        )
        
        total_present_days = student_in_records.values('timestamp__date').distinct().count()
        
        # Get all unique dates when attendance was recorded (for any student)
        # This represents total class days
        all_class_dates = AttendanceRecord.objects.filter(
            attendance_type='IN',
            granted=True
        ).values('timestamp__date').distinct().count()
        
        # Fallback: if no class dates recorded yet, use 1 to avoid division by zero
        max_possible_days = max(1, all_class_dates)
        
        attendance_percentage = (total_present_days / max_possible_days * 100) if max_possible_days > 0 else 0
        attendance_percentage = min(100, attendance_percentage)  # Cap at 100%
        
        # Determine if present today
        today_present = class_in is not None and class_in.granted
        
        stat = {
            'student': student,
            'today_attendance': today_present,
            'class_in_time': class_in.timestamp.strftime('%H:%M') if class_in else '--',
            'class_out_time': class_out.timestamp.strftime('%H:%M') if class_out else '--',
            'is_late': class_in.is_late if class_in else False,
            'left_early': class_out.is_early_departure if class_out else False,
            'attendance_percentage': attendance_percentage,
        }
        student_stats.append(stat)

    # Calculate present today count
    present_today = sum(1 for stat in student_stats if stat['today_attendance'])

    context = {
        'student_stats': student_stats,
        'total_students': total_students,
        'present_today': present_today,
        'today': filter_date,
        'date_filter': selected_date or filter_date.isoformat(),
    }
    
    return render(request, 'accounts/teacher_dashboard.html', context)
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect

def teacher_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role == 'teacher':
                login(request, user)
                return redirect('teacher_dashboard')
            else:
                messages.error(request, "Only teachers can login here")
                return render(request, 'accounts/teacher_login.html', {'form': form})
        else:
            messages.error(request, "Invalid username or password")
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/teacher_login.html', {'form': form})

from django.contrib import messages

def teacher_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        if password1 != password2:
            messages.error(request, "Passwords don't match")
            return render(request, 'accounts/teacher_signup.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return render(request, 'accounts/teacher_signup.html')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            role='teacher'
        )

        login(request, user)
        return redirect('teacher_dashboard')

    return render(request, 'accounts/teacher_signup.html')