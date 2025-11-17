from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import EnrollmentSerializer
from .models import User
from attendance.utils import base64_to_pil, detect_and_crop_face, compute_phash, phash_to_hex
from django.core.files.base import ContentFile
from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url
from PIL import Image
import io
from django.contrib.auth import logout
from django.shortcuts import redirect


class EnrollUserView(APIView):
    permission_classes = [permissions.AllowAny]  # restrict in production

    def post(self, request):
        # Expecting multipart/form-data (with image_file)
        username = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role")
        rfid_uid = request.POST.get("rfid_uid")
        image_file = request.FILES.get("image_file")

        # Validation
        if not all([username, password, role, rfid_uid, image_file]):
            return Response(
                {"detail": "All fields are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {"detail": "username exists"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if User.objects.filter(rfid_uid=rfid_uid).exists():
            return Response(
                {"detail": "rfid exists"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Read uploaded file directly as PIL image
            pil_img = Image.open(image_file).convert("RGB")

            # Detect and crop face
            cropped = detect_and_crop_face(pil_img)
            if cropped is None:
                return Response(
                    {"detail": "no face found in enrollment image"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Compute perceptual hash
            ph = compute_phash(cropped)
            ph_hex = ph.__str__()
            
        except Exception as e:
            return Response(
                {"detail": f"invalid image: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Create the new user
        user = User.objects.create_user(
            username=username,
            password=password,
            role=role,
            rfid_uid=rfid_uid,
        )
        user.face_hash = ph_hex

        try:
            # Convert cropped image to bytes for Cloudinary upload
            img_io = io.BytesIO()
            cropped.save(img_io, format="JPEG")
            img_io.seek(0)
            
            # Upload to Cloudinary
            upload_response = upload(
                img_io,
                folder='faces/',
                public_id=f"{username}_face",
                resource_type='image',
                overwrite=True
            )
            
            # Get the secure URL from Cloudinary
            cloudinary_url_str = upload_response['secure_url']
            
            # Save the Cloudinary URL to the user model
            user.face_image = cloudinary_url_str
            user.save()
            
            return Response({
                "detail": "user enrolled successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "rfid_uid": user.rfid_uid,
                    "face_hash": user.face_hash,
                    "image_url": cloudinary_url_str,
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Delete user if upload fails
            user.delete()
            return Response(
                {"detail": f"Failed to upload image: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


def student_enroll_page(request):
    return render(request, "enroll_student.html")


def logout_view(request):
    logout(request)
    return redirect('teacher_login')