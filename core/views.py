from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render
from django.db import transaction
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from django.db.models.functions import ExtractWeekDay, ExtractHour
from datetime import timedelta, datetime
from .models import EspacioEstacionamiento, Reserva
from .serializers import EspacioSerializer, ReservaSerializer, CrearReservaSerializer
from .services import ReservaService
from notifications.email_service import EmailService
import logging

logger = logging.getLogger(__name__)


def dashboard_view(request):
    """Vista para el dashboard"""
    return render(request, 'dashboard.html')


class EspacioViewSet(viewsets.ReadOnlyModelViewSet):
    """API para consultar espacios de estacionamiento"""
    queryset = EspacioEstacionamiento.objects.all()
    serializer_class = EspacioSerializer


class ReservaViewSet(viewsets.ModelViewSet):
    """API para gestionar reservas"""
    queryset = Reserva.objects.all()
    serializer_class = ReservaSerializer
    
    @action(detail=False, methods=['post'])
    def verificar(self, request):
        """
        Verifica disponibilidad de un espacio
        """
        try:
            espacio_numero = request.data.get('espacio_numero')
            fecha = request.data.get('fecha')
            hora = request.data.get('hora')
            duracion = int(request.data.get('duracion', 0))
            
            if not all([espacio_numero, fecha, hora, duracion]):
                return Response({
                    'success': False,
                    'error': 'Faltan parámetros: espacio_numero, fecha, hora, duracion'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            disponible, mensaje, conflictos = ReservaService.verificar_disponibilidad(
                espacio_numero, fecha, hora, duracion
            )
            
            return Response({
                'success': True,
                'disponible': disponible,
                'mensaje': mensaje,
                'conflictos': ReservaSerializer(conflictos, many=True).data if conflictos else []
            })
            
        except Exception as e:
            logger.error(f"Error en verificar disponibilidad: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def crear(self, request):
        """
        Crea una nueva reserva
        """
        try:
            # Validar datos con serializer
            serializer = CrearReservaSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Crear reserva
            reserva = ReservaService.crear_reserva(
                serializer.validated_data,
                usuario=request.user if request.user.is_authenticated else None
            )
            
            return Response({
                'success': True,
                'mensaje': '✅ Reserva creada exitosamente',
                'reserva': ReservaSerializer(reserva).data
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creando reserva: {e}")
            return Response({
                'success': False,
                'error': 'Error interno del servidor'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ================================================================
    # ✅ CANCELAR RESERVA
    # ================================================================
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancela una reserva y libera el espacio
        POST /api/reservas/{id}/cancelar/
        """
        try:
            reserva = self.get_object()
            
            # Verificar si ya está cancelada
            if reserva.cancelada:
                return Response({
                    'success': False,
                    'error': 'La reserva ya está cancelada'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                # Marcar como cancelada
                reserva.cancelada = True
                reserva.save()

                # ✅ Enviar email de cancelación
                EmailService.enviar_cancelacion_reserva(reserva)
                
                # Liberar el espacio si está reservado
                if reserva.espacio.estado == 'RESERVADO':
                    reserva.espacio.estado = 'LIBRE'
                    reserva.espacio.save()
                    logger.info(f"🔓 Espacio {reserva.espacio.numero} liberado (reserva {reserva.id} cancelada)")
                
                return Response({
                    'success': True,
                    'mensaje': f'✅ Reserva {reserva.id} cancelada exitosamente',
                    'espacio_liberado': reserva.espacio.numero,
                    'reserva': ReservaSerializer(reserva).data
                })
                
        except Exception as e:
            logger.error(f"Error cancelando reserva: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class EstadisticaViewSet(viewsets.GenericViewSet):
    """API para estadísticas y forecasting"""
    permission_classes = [permissions.AllowAny]
    queryset = Reserva.objects.all()
    
    @action(detail=False, methods=['get'])
    def por_horario(self, request):
        """
        Distribución de reservas por hora del día (hoy)
        GET /api/estadisticas/por_horario/
        """
        try:
            from django.db.models.functions import ExtractHour
            
            hoy = timezone.now().date()
            
            # ✅ Cambiar alias a 'hora_del_dia' (no choca con el campo 'hora')
            reservas = (
                Reserva.objects
                .filter(fecha=hoy)
                .annotate(hora_del_dia=ExtractHour('hora'))  # ← ALIAS DIFERENTE
                .values('hora_del_dia')
                .annotate(
                    total_reservas=Count('id'),
                    minutos_totales=Sum('duracion')
                )
                .order_by('hora_del_dia')
            )
            
            # Preparar arrays de 24 horas
            labels = [f'{h:02d}:00' for h in range(24)]
            reservas_data = [0] * 24
            minutos_data = [0] * 24
            
            for r in reservas:
                h = r['hora_del_dia']  # ← USAR EL NUEVO ALIAS
                reservas_data[h] = r['total_reservas']
                minutos_data[h] = r['minutos_totales'] or 0
            
            # Calcular hora pico
            hora_pico = ''
            if reservas_data and max(reservas_data) > 0:
                max_idx = reservas_data.index(max(reservas_data))
                hora_pico = labels[max_idx]
            else:
                hora_pico = 'N/A'
            
            return Response({
                'success': True,
                'grafico': {
                    'labels': labels,
                    'datasets': [
                        {
                            'label': 'Número de Reservas',
                            'data': reservas_data,
                            'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                            'borderColor': 'rgba(54, 162, 235, 1)',
                            'borderWidth': 1,
                            'type': 'bar'
                        },
                        {
                            'label': 'Minutos Ocupados',
                            'data': minutos_data,
                            'backgroundColor': 'rgba(255, 99, 132, 0.5)',
                            'borderColor': 'rgba(255, 99, 132, 1)',
                            'borderWidth': 1,
                            'type': 'line',
                            'yAxisID': 'y1'
                        }
                    ]
                },
                'estadisticas': {
                    'total_reservas_hoy': sum(reservas_data),
                    'total_minutos_hoy': sum(minutos_data),
                    'hora_pico': hora_pico
                }
            })
            
        except Exception as e:
            logger.error(f"Error en por_horario: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def por_espacio(self, request):
        """
        Ocupación por espacio (últimos 7 días)
        GET /api/estadisticas/por_espacio/
        """
        try:
            hoy = timezone.now().date()
            hace_7_dias = hoy - timedelta(days=7)
            
            # Reservas por espacio en los últimos 7 días
            reservas = Reserva.objects.filter(
                fecha__gte=hace_7_dias,
                fecha__lte=hoy
            ).values('espacio__numero').annotate(
                total_reservas=Count('id'),
                minutos_ocupados=Sum('duracion')
            ).order_by('espacio__numero')
            
            # Calcular porcentaje de ocupación (sobre 24h * 7 días = 10080 min)
            total_minutos_disponibles = 7 * 24 * 60  # 10080 minutos
            
            labels = []
            reservas_data = []
            minutos_data = []
            porcentaje_data = []
            
            for r in reservas:
                espacio_num = r['espacio__numero']
                labels.append(f'Espacio {espacio_num}')
                reservas_data.append(r['total_reservas'])
                minutos_data.append(r['minutos_ocupados'] or 0)
                
                porcentaje = (r['minutos_ocupados'] or 0) / total_minutos_disponibles * 100
                porcentaje_data.append(round(porcentaje, 2))
            
            # Espacio más y menos solicitado
            espacio_mas = labels[reservas_data.index(max(reservas_data))] if reservas_data else 'N/A'
            espacio_menos = labels[reservas_data.index(min(reservas_data))] if reservas_data else 'N/A'
            ocupacion_promedio = round(sum(porcentaje_data) / len(porcentaje_data), 2) if porcentaje_data else 0
            
            return Response({
                'success': True,
                'grafico': {
                    'labels': labels,
                    'datasets': [
                        {
                            'label': 'Total Reservas (7 días)',
                            'data': reservas_data,
                            'backgroundColor': 'rgba(75, 192, 192, 0.6)',
                            'borderColor': 'rgba(75, 192, 192, 1)',
                            'borderWidth': 1,
                            'type': 'bar'
                        },
                        {
                            'label': '% Ocupación',
                            'data': porcentaje_data,
                            'backgroundColor': 'rgba(255, 159, 64, 0.6)',
                            'borderColor': 'rgba(255, 159, 64, 1)',
                            'borderWidth': 1,
                            'type': 'line',
                            'yAxisID': 'y1'
                        }
                    ]
                },
                'estadisticas': {
                    'espacio_mas_solicitado': espacio_mas,
                    'espacio_menos_solicitado': espacio_menos,
                    'ocupacion_promedio': f'{ocupacion_promedio}%'
                }
            })
            
        except Exception as e:
            logger.error(f"Error en por_espacio: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def forecasting(self, request):
        """
        Predicción de demanda por día de la semana (últimos 30 días)
        GET /api/estadisticas/forecasting/
        """
        try:
            hoy = timezone.now().date()
            hace_30_dias = hoy - timedelta(days=30)
            
            # ✅ Usando ORM de Django (sin SQL crudo)
            reservas = (
                Reserva.objects
                .filter(
                    fecha__gte=hace_30_dias,
                    fecha__lte=hoy
                )
                .annotate(
                    dia_semana=ExtractWeekDay('fecha')  # 1=Domingo, 7=Sábado en Django
                )
                .values('dia_semana')
                .annotate(
                    total_reservas=Count('id'),
                    duracion_promedio=Avg('duracion'),
                    espacios_utilizados=Count('espacio', distinct=True)
                )
                .order_by('dia_semana')
            )
            
            # Nombres de los días (Django: 1=Domingo, 7=Sábado)
            dias = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
            
            # Inicializar arrays (índice 0 = Domingo)
            reservas_data = [0] * 7
            duracion_data = [0] * 7
            espacios_data = [0] * 7
            
            for r in reservas:
                dia_idx = r['dia_semana'] - 1  # Convertir 1-7 a 0-6
                reservas_data[dia_idx] = r['total_reservas']
                duracion_data[dia_idx] = round(r['duracion_promedio'] or 0, 1)
                espacios_data[dia_idx] = r['espacios_utilizados']
            
            # Día más y menos ocupado
            dia_mas = dias[reservas_data.index(max(reservas_data))] if max(reservas_data) > 0 else 'N/A'
            dia_menos = dias[reservas_data.index(min(reservas_data))] if min(reservas_data) > 0 else 'N/A'
            promedio_diario = round(sum(reservas_data) / 7, 1)
            
            return Response({
                'success': True,
                'grafico': {
                    'labels': dias,
                    'datasets': [
                        {
                            'label': 'Reservas por día',
                            'data': reservas_data,
                            'backgroundColor': 'rgba(153, 102, 255, 0.6)',
                            'borderColor': 'rgba(153, 102, 255, 1)',
                            'borderWidth': 1,
                            'type': 'bar'
                        },
                        {
                            'label': 'Duración promedio (min)',
                            'data': duracion_data,
                            'backgroundColor': 'rgba(255, 205, 86, 0.6)',
                            'borderColor': 'rgba(255, 205, 86, 1)',
                            'borderWidth': 1,
                            'type': 'line',
                            'yAxisID': 'y1'
                        }
                    ]
                },
                'estadisticas': {
                    'dia_mas_ocupado': dia_mas,
                    'dia_menos_ocupado': dia_menos,
                    'promedio_reservas_diarias': promedio_diario,
                    'total_espacios_utilizados': max(espacios_data) if espacios_data else 0
                }
            })
            
        except Exception as e:
            logger.error(f"Error en forecasting: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

    


    @action(detail=False, methods=['post'], url_path='enviar_reporte')  # ✅ 'post' es correcto
    def enviar_reporte(self, request):
        """
        Genera y envía el reporte semanal por email
        POST /api/estadisticas/enviar_reporte/
        """
        try:
            from reports.report_service import ReportService
            from reports.pdf_generator import PDFGenerator
            from notifications.email_service import EmailService
            
            # 1. Generar datos
            reporte_data = ReportService.generar_reporte_semanal()
            
            if not reporte_data:
                return Response({
                    'success': False,
                    'error': 'No se pudieron generar los datos del reporte'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 2. Generar PDF
            pdf_buffer = PDFGenerator.generar_reporte_pdf(reporte_data)
            
            # 3. Enviar email
            EmailService.enviar_reporte_semanal(reporte_data, pdf_buffer)
            
            return Response({
                'success': True,
                'mensaje': '✅ Reporte enviado correctamente',
                'periodo': reporte_data['periodo']
            })
            
        except Exception as e:
            logger.error(f"Error enviando reporte: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def analisis_view(request):
        """Vista para el dashboard de análisis"""
        return render(request, 'analisis.html')

# core/views.py - Agregar al final

import json
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from datetime import datetime
from .models import EspacioEstacionamiento

class SensorViewSet(viewsets.GenericViewSet):
    """
    API para recibir datos de sensores (SIM800L)
    """
    permission_classes = [permissions.AllowAny]
    queryset = EspacioEstacionamiento.objects.none()  # La autenticación es por token

    @action(detail=False, methods=['post'], url_path='estado')
    def recibir_estado(self, request):
        """
        Recibe datos de un sensor (SIM800L/Arduino)
        POST /api/sensor/estado/
        """
        try:
            # ============================================================
            # 1. VALIDAR TOKEN
            # ============================================================
            token = request.headers.get('X-Sensor-Token')
            if not token or token != settings.SENSOR_TOKEN:
                return Response({
                    'success': False,
                    'error': 'Token inválido o no proporcionado'
                }, status=status.HTTP_401_UNAUTHORIZED)

            # ============================================================
            # 2. OBTENER DATOS DEL REQUEST
            # ============================================================
            data = request.data

            # Validar que el JSON tenga los campos necesarios
            if 'id' not in data or 'estado' not in data:
                return Response({
                    'success': False,
                    'error': 'Faltan campos: id y estado son requeridos'
                }, status=status.HTTP_400_BAD_REQUEST)

            sensor_id = int(data['id'])
            estado = data['estado'].upper()
            timestamp = data.get('timestamp', datetime.now().isoformat())
            patente = data.get('patente', '')  # Opcional para lecturas con patente

            # ============================================================
            # 3. VALIDAR QUE EL ESTADO SEA VÁLIDO
            # ============================================================
            estados_validos = ['LIBRE', 'OCUPADO', 'RESERVADO']
            if estado not in estados_validos:
                return Response({
                    'success': False,
                    'error': f'Estado inválido. Valores permitidos: {estados_validos}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # ============================================================
            # 4. BUSCAR O CREAR ESPACIO
            # ============================================================
            espacio, created = EspacioEstacionamiento.objects.get_or_create(
                numero=sensor_id,
                defaults={
                    'estado': estado,
                    'sensor_conectado': True,
                    'ultimo_heartbeat': timezone.now()
                }
            )

            # ============================================================
            # 5. ACTUALIZAR ESTADO (CON LÓGICA DE RESERVAS)
            # ============================================================
            from django.db import transaction
            from .models import Reserva

            with transaction.atomic():
                # ✅ Si el sensor detecta LIBRE y hay una reserva espontánea activa
                if estado == 'LIBRE':
                    reserva_espontanea = Reserva.objects.filter(
                        espacio=espacio,
                        cancelada=False,
                        tipo='espontanea'
                    ).first()

                    if reserva_espontanea:
                        reserva_espontanea.cancelada = True
                        reserva_espontanea.save()
                        logger.info(f"🔓 Reserva espontánea {reserva_espontanea.id} liberada por sensor")

                # ✅ Si el sensor detecta OCUPADO y el espacio está RESERVADO
                elif estado == 'OCUPADO':
                    # Verificar si hay una reserva activa (programada o espontánea)
                    reserva_activa = Reserva.objects.filter(
                        espacio=espacio,
                        cancelada=False,
                        fecha=timezone.now().date()
                    ).first()

                    if reserva_activa:
                        logger.info(f"✅ Espacio {sensor_id} ocupado por reserva {reserva_activa.id}")

                # ✅ Si el estado cambia, actualizar (si no está RESERVADO)
                if espacio.estado != 'RESERVADO' or estado == 'OCUPADO':
                    espacio.estado = estado
                    espacio.sensor_conectado = True
                    espacio.ultimo_heartbeat = timezone.now()
                    espacio.save()

            # ============================================================
            # 6. LOG Y RESPUESTA
            # ============================================================
            logger.info(f"📡 Sensor {sensor_id} → {estado} (timestamp: {timestamp})")

            return Response({
                'success': True,
                'mensaje': f'✅ Estado del sensor {sensor_id} actualizado: {estado}',
                'data': {
                    'sensor_id': sensor_id,
                    'estado': estado,
                    'timestamp': timestamp,
                    'espacio_id': espacio.id
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"❌ Error en recibir_estado: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)