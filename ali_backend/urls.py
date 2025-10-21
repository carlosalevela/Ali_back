# ali_backend/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse, Http404
from django.contrib.staticfiles.storage import staticfiles_storage

from Usuario import urls as urls_usuarios
from test_grado9 import urls as urls_tests_grado9
from test_grado_10_11 import urls as urls_tests_grado10_11

urlpatterns = [
    path('admin/', admin.site.urls),
    path('Alipsicoorientadora/usuarios/', include(urls_usuarios)),
    path('Alipsicoorientadora/tests-grado9/', include(urls_tests_grado9)),
    path('Alipsicoorientadora/tests-grado10-11/', include(urls_tests_grado10_11)),
]