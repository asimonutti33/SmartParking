from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EspacioViewSet, ReservaViewSet, dashboard_view, EstadisticaViewSet, analisis_view, SensorViewSet

router = DefaultRouter()
router.register(r'espacios', EspacioViewSet, basename='espacios')
router.register(r'reservas', ReservaViewSet, basename='reservas')
router.register(r'estadisticas', EstadisticaViewSet, basename='estadisticas')
router.register(r'sensor', SensorViewSet, basename='sensor')

urlpatterns = [
    # Dashboard en la raíz
    path('', dashboard_view, name='dashboard'),
    path('analisis/', analisis_view, name='analisis'),
    # API bajo /api/
    path('api/', include(router.urls)),
    path('api/estadisticas/enviar_reporte/', EstadisticaViewSet.as_view({'post': 'enviar_reporte'}), name='estadisticas-enviar_reporte'),
]