import json
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from Usuario.models import Usuario

class TestUsuarioAPI(TestCase):
    def setUp(self):
        """Se ejecuta antes de cada prueba para garantizar un estado limpio."""
        self.client = APIClient()

        # Crear usuarios de prueba
        self.admin_user = Usuario.objects.create_user(
            username='admin_user',
            nombre='Admin',
            email='admin@example.com',
            rol='admin',
            grado='0',
            edad=30,
            password='adminpass'
        )

        self.estudiante_user = Usuario.objects.create_user(
            username='estudiante_user',
            nombre='Estudiante',
            email='estu@example.com',
            rol='estudiante',
            grado='10',
            edad=16,
            password='estupass'
        )

    def test_obtener_lista_usuarios_sin_auth(self):
        """Verifica que un usuario no autenticado no pueda obtener la lista de usuarios."""
        response = self.client.get(reverse('lista_usuarios'))
        self.assertEqual(response.status_code, 403)  # Django devuelve 403 Forbidden en lugar de 401

    def test_obtener_lista_usuarios_admin(self):
        """Verifica que un admin autenticado pueda ver la lista de usuarios."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(reverse('lista_usuarios'))
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.data), 0)

    def test_registro_usuario(self):
        """Verifica que un usuario pueda registrarse correctamente."""
        data = {
            'username': 'nuevo_usuario',
            'nombre': 'Nuevo',
            'email': 'nuevo@example.com',
            'rol': 'estudiante',
            'grado': '11',
            'edad': 17,
            'password': 'testpass123'
        }
        response = self.client.post(reverse('registro'), data)  # Cambio de 'lista_usuarios' a 'registro'
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Usuario.objects.filter(username='nuevo_usuario').exists())

    def test_obtener_detalle_usuario(self):
        """Verifica que un admin pueda obtener los detalles de un usuario."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(reverse('detalle_usuario', kwargs={'pkid': self.estudiante_user.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], self.estudiante_user.username)


    def test_eliminar_usuario(self):
        """Verifica que un admin pueda eliminar un usuario."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(reverse('detalle_usuario', kwargs={'pkid': self.estudiante_user.id}))
        self.assertEqual(response.status_code, 200)  
        self.assertFalse(Usuario.objects.filter(id=self.estudiante_user.id).exists())
