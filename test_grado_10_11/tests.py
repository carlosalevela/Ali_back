from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from rest_framework.test import APITestCase
from Usuario.models import Usuario
from test_grado_10_11.models import TestGrado10_11

class TestGrado10_11Tests(APITestCase):

    def setUp(self):
        self.user = Usuario.objects.create_user(
            username='tester10_11',
            email='tester10_11@example.com',
            password='testpass'
        )

        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

        self.url = reverse('testgrado10_11-list')  # Este nombre depende de tu router

        self.respuestas_validas = {
            f"pregunta_{i}": "C" for i in range(1, 41)
        }

        self.test_grado10_11 = TestGrado10_11.objects.create(
            usuario=self.user,
            respuestas=self.respuestas_validas,
            resultado="Ingeniería"  # Ajusta según el modelo entrenado
        )

    def test_creacion_exitosa_test(self):
        data = {
            "respuestas": self.respuestas_validas,
            "usuario": self.user.id
        }
        response = self.client.post(self.url, data, format='json')
        print("Response data:", response.data)
        self.assertEqual(response.status_code, 201)
        self.assertIn("resultado", response.data)

    def test_obtener_resultado_usuario(self):
        detail_url = reverse('testgrado10_11-detail', args=[self.test_grado10_11.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.test_grado10_11.id)
        self.assertEqual(response.data['resultado'], "Ingeniería")

    def test_error_por_respuestas_incompletas(self):
        respuestas_incompletas = {
            f"pregunta_{i}": "B" for i in range(1, 30)  # solo 29 respuestas
        }
        data = {"respuestas": respuestas_incompletas, "usuario": self.user.id}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['resultado'], "Error: Faltan respuestas en la solicitud")

    def test_error_por_respuestas_invalidas(self):
        respuestas_invalidas = {
            f"pregunta_{i}": "X" for i in range(1, 41)  # valores no válidos
        }
        data = {"respuestas": respuestas_invalidas, "usuario": self.user.id}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['resultado'], "Error: Las respuestas deben ser solo A, B, C o D")
