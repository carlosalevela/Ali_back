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

# ===== SPA catch-all (debe ir AL FINAL) =====
def spa_index(_request):
    try:
        # Sirve el index generado por Flutter que el CI copia a static/app/
        with staticfiles_storage.open("app/index.html") as f:
            return HttpResponse(f.read(), content_type="text/html")
    except Exception:
        raise Http404("SPA no generada (falta static/app/index.html)")

urlpatterns += [
    # Excluye admin, static y tu prefijo de API para no interferir
    re_path(r"^(?!admin/|static/|Alipsicoorientadora/).*$", spa_index),
]
