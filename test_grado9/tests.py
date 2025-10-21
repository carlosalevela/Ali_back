from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from rest_framework.test import APITestCase
from Usuario.models import Usuario
from test_grado9.models import TestGrado9

class TestGrado9Tests(APITestCase):

    def setUp(self):
        # Crear usuario con email porque tu modelo lo requiere
        self.user = Usuario.objects.create_user(
            username='tester',
            email='tester@example.com',
            password='testpass'
        )

        # Crear un JWT para el usuario
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)  # Obtener solo el access_token

        # Asegura que el token JWT se use correctamente en las peticiones
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

        # URL generada por el router
        self.url = reverse('test_grado9-list')

        # Diccionario de respuestas válidas para 40 preguntas
        self.respuestas_validas = {
            f"pregunta_{i}": "D" for i in range(1, 41)
        }

        # Crear el objeto TestGrado9 asociado al usuario
        self.test_grado9 = TestGrado9.objects.create(
            usuario=self.user,
            respuestas=self.respuestas_validas,
            resultado="Industrial"  # Puedes poner el resultado que desees
        )

    def test_creacion_exitosa_test(self):
        data = {
            "respuestas": self.respuestas_validas,
            "usuario": self.user.id
        }
        response = self.client.post(self.url, data, format='json')
        print(response.data)  
        self.assertEqual(response.status_code, 201)
        self.assertIn("resultado", response.data)

    def test_obtener_resultado_usuario(self):
        response = self.client.get(reverse('test_grado9-detail', args=[self.test_grado9.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.test_grado9.id)
        self.assertEqual(response.data['resultado'], "Industrial")  # El resultado que asignaste
