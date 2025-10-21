from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import PasswordResetRequestSerializer, SetNewPasswordSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator

import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

# ===== IMPORTS EXTRA PARA RESET PASSWORD =====
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import smart_bytes, force_str

from Usuario.models import Usuario, Grade  # ajusta si Grade está en otra app
from Usuario.serializers import (
    UsuarioSerializer,
    GradeSerializerMini,     # admin (completo)
    PublicGradeSerializer,   # no admin (recortado)
)

# ==========================
#  LOGGING / AUTH UTILS
# ==========================
logger = logging.getLogger(__name__)
User = get_user_model()
token_generator = PasswordResetTokenGenerator()

# ==========================
#  AUTH (JWT) con claims extra
# ==========================
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['rol'] = user.rol
        token['nombre'] = user.nombre
        token['grado'] = user.grado
        token['edad'] = user.edad
        token['user_id'] = user.id
        return token

class LoginAPI(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# ==========================
#  USUARIOS
# ==========================
class UsuarioAPI(APIView):
    """
    GET  /usuarios/usuarios/        -> Lista (solo admin)
    POST /usuarios/usuarios/        -> Registro (abierto)
    """
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        # POST de registro es público; el resto autenticado
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAuthenticated()]

    # LISTAR (solo admin)
    def get(self, request):
        if not request.user.is_authenticated or request.user.rol != "admin":
            return Response(
                {"error": "No tienes permiso para ver esta lista"},
                status=status.HTTP_403_FORBIDDEN,
            )

        nombre = request.query_params.get("nombre", "").strip()
        email = request.query_params.get("email", "").strip()
        username = request.query_params.get("username", "").strip()

        usuarios = Usuario.objects.all()
        if nombre:
            usuarios = usuarios.filter(nombre__icontains=nombre)
        if email:
            usuarios = usuarios.filter(email__icontains=email)
        if username:
            usuarios = usuarios.filter(username__icontains=username)

        serializer = UsuarioSerializer(usuarios, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # REGISTRO (abierto)
    def post(self, request, *args, **kwargs):
        data = {
            'username': request.data.get('username'),
            'nombre': request.data.get('nombre'),
            'email': request.data.get('email'),
            'rol': 'estudiante',  # por defecto estudiante
            'grado': request.data.get('grado'),
            'edad': request.data.get('edad'),
            'password': request.data.get('password'),
            # permitir asignar un grado por id desde el registro (opcional)
            'grade_ref_id': request.data.get('grade_ref_id'),
        }

        serializador = UsuarioSerializer(data=data, context={"request": request})
        if serializador.is_valid():
            usuario = serializador.save()
            # set_password ya se maneja en el serializer; refuerzo por seguridad
            if data.get('password'):
                usuario.set_password(data['password'])
                usuario.save()
            return Response(serializador.data, status=status.HTTP_201_CREATED)
        return Response(serializador.errors, status=status.HTTP_400_BAD_REQUEST)


class UsuarioDetailAPI(APIView):
    """
    GET    /usuarios/usuarios/<id>/   -> Detalle (auth)
    PUT    /usuarios/usuarios/<id>/   -> Editar (admin o dueño)
    DELETE /usuarios/usuarios/<id>/   -> Eliminar (solo admin)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pkid, *args, **kwargs):
        usuario = get_object_or_404(Usuario, id=pkid)
        serializador = UsuarioSerializer(usuario, context={"request": request})
        return Response(serializador.data, status=status.HTTP_200_OK)

    def put(self, request, pkid):
        usuario = get_object_or_404(Usuario, id=pkid)

        if request.user.rol != "admin" and request.user.id != usuario.id:
            return Response(
                {"error": "No tienes permiso para editar este usuario"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializador = UsuarioSerializer(usuario, data=request.data, partial=True, context={"request": request})
        if serializador.is_valid():
            serializador.save()
            return Response(serializador.data, status=status.HTTP_200_OK)

        print("Errores de validación:", serializador.errors)
        return Response(serializador.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pkid):
        usuario = get_object_or_404(Usuario, id=pkid)

        if request.user.rol != "admin":
            return Response(
                {"error": "No tienes permiso para eliminar usuarios"},
                status=status.HTTP_403_FORBIDDEN,
            )

        usuario.delete()
        # Mantengo 200 para no romper tu Flutter actual
        return Response({"message": "Usuario eliminado"}, status=status.HTTP_200_OK)


# ==========================
#  GRADOS (CRUD)
# ==========================
class GradesAPI(APIView):
    """
    GET  /grados/        -> Lista
        - admin: ve todos los campos de todos los grados
        - no admin: ve SOLO (id, code, section) y SOLO grados activos
        Filtros: ?code=10&section=A&active=true|false (active solo afecta a admin)
    POST /grados/        -> Crear (solo admin)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = request.query_params.get("code", "").strip()
        section = request.query_params.get("section", "").strip()
        active = request.query_params.get("active", "").strip().lower()

        qs = Grade.objects.all()

        is_admin = (request.user and getattr(request.user, "rol", "") == "admin")
        # No admin: solo activos
        if not is_admin:
            qs = qs.filter(is_active=True)

        if code:
            qs = qs.filter(code__icontains=code)
        if section:
            qs = qs.filter(section__icontains=section)
        # El filtro 'active' solo lo permitimos a admin para ver inactivos si quiere
        if active in ("true", "false") and is_admin:
            qs = qs.filter(is_active=(active == "true"))

        if is_admin:
            ser = GradeSerializerMini(qs, many=True)
        else:
            ser = PublicGradeSerializer(qs, many=True)

        return Response(ser.data, status=status.HTTP_200_OK)

    def post(self, request):
        if getattr(request.user, "rol", "") != "admin":
            return Response(
                {"error": "Solo admin puede crear grados"},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = GradeSerializerMini(data=request.data)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=status.HTTP_201_CREATED)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class GradeDetailAPI(APIView):
    """
    GET    /grados/<id>/ -> Detalle
        - admin: ve todos los campos
        - no admin: SOLO (id, code, section) y SOLO si el grado está activo
    PUT    /grados/<id>/ -> Actualizar (solo admin)
    DELETE /grados/<id>/ -> Eliminar (solo admin)
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pkid):
        return get_object_or_404(Grade, id=pkid)

    def get(self, request, pkid):
        g = self.get_object(pkid)
        is_admin = (request.user and getattr(request.user, "rol", "") == "admin")

        # No admin no puede ver grados inactivos
        if not is_admin and not g.is_active:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)

        ser = GradeSerializerMini(g) if is_admin else PublicGradeSerializer(g)
        return Response(ser.data, status=status.HTTP_200_OK)

    def put(self, request, pkid):
        if getattr(request.user, "rol", "") != "admin":
            return Response(
                {"error": "Solo admin puede actualizar grados"},
                status=status.HTTP_403_FORBIDDEN,
            )
        g = self.get_object(pkid)
        ser = GradeSerializerMini(g, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=status.HTTP_200_OK)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pkid):
        if getattr(request.user, "rol", "") != "admin":
            return Response(
                {"error": "Solo admin puede eliminar grados"},
                status=status.HTTP_403_FORBIDDEN,
            )
        g = self.get_object(pkid)
        g.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==========================
#  RESET PASSWORD
# ==========================
class PasswordResetRequestView(APIView):
    """
    POST /auth/password-reset/
    body: { "email": "usuario@correo.com" }
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        # 1) Validar entrada
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip()

        # 2) Buscar usuario (sin revelar existencia)
        try:
            user = User.objects.filter(email__iexact=email, is_active=True).first()
        except Exception:
            logger.exception("Error buscando usuario por email")
            user = None

        if not user:
            # Siempre 200 para no filtrar si el correo existe
            return Response(
                {"detail": "Si el correo existe en nuestro sistema, enviaremos un enlace para restablecer la contraseña."},
                status=status.HTTP_200_OK
            )

        # 3) Generar uid/token y armar el enlace (USANDO URL FIJA DE settings.FRONTEND_RESET_URL)
        uidb64 = urlsafe_base64_encode(smart_bytes(user.pk))
        token = token_generator.make_token(user)

        base_url = getattr(settings, "FRONTEND_RESET_URL", "").rstrip("/")
        reset_link = f"{base_url}?uid={uidb64}&token={token}" if base_url else f"/?uid={uidb64}&token={token}"

        # 4) Construir email (texto + HTML)
        subject = "Recuperación de contraseña - ALI"
        text = (
            "Hola,\n\n"
            "Recibimos una solicitud para restablecer tu contraseña.\n"
            f"Usa este enlace:\n{reset_link}\n\n"
            "Si no fuiste tú, ignora este correo."
        )
        html = f"""
            <p>Hola,</p>
            <p>Recibimos una solicitud para restablecer tu contraseña.</p>
            <p><a href="{reset_link}" target="_blank">Haz clic aquí para restablecerla</a></p>
            <p>Si no fuiste tú, ignora este correo.</p>
        """

        # 5) Enviar (sin silenciar errores para ver el problema real en consola)
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.EMAIL_HOST_USER
        msg = EmailMultiAlternatives(subject, text, from_email, [email])
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)

        # 6) En DEBUG devolvemos datos útiles para pruebas
        if settings.DEBUG:
            return Response(
                {"detail": "Correo enviado (DEBUG).", "uid": uidb64, "token": token, "reset_link": reset_link},
                status=status.HTTP_200_OK
            )

        return Response(
            {"detail": "Si el correo existe en nuestro sistema, enviaremos un enlace para restablecer la contraseña."},
            status=status.HTTP_200_OK
        )


class SetNewPasswordView(APIView):
    """
    POST /auth/password-reset/confirm/
    body: { "uid": "<uidb64>", "token": "<token>", "password": "NuevaPass123" }
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        ser = SetNewPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        uidb64 = ser.validated_data["uid"]
        token = ser.validated_data["token"]
        new_password = ser.validated_data["new_password"]

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid, is_active=True)
        except Exception:
            logger.exception("UID inválido en reset de contraseña")
            return Response({"detail": "Enlace inválido."}, status=status.HTTP_400_BAD_REQUEST)

        if not token_generator.check_token(user, token):
            return Response({"detail": "Token inválido o expirado."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Contraseña actualizada correctamente."}, status=status.HTTP_200_OK)
