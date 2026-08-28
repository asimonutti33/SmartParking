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
from notifications.telegram_service import TelegramService
import logging
import json
from django.conf import settings

logger = logging.getLogger(__name__)

# ============================================================
# ✅ ESTADO DE CONEXIONES (en memoria)
# ============================================================
ULTIMO_HEARTBEAT = {}      # {raspberry_id: timestamp}
ULTIMO_ESTADO_ARDUINO = {} # {raspberry_id: {'conectado': bool, 'ultimo_dato': timestamp}}
ALERTA_ENVIADA = {}        # {raspberry_id: {'arduino': bool, 'raspberry': bool}}


def dashboard_view(request):
    """Vista para el dashboard"""
    return render(request, 'dashboard.html')


def analisis_view(request):
    """Vista para el dashboard de análisis"""
    return render(request, 'analisis.html')


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
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancela una reserva y libera el espacio
        POST /api/reservas/{id}/cancelar/
        """
        try:
            reserva = self.get_object()
            
            if reserva.cancelada:
                return Response({
                    'success': False,
                    'error': 'La reserva ya está cancelada'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                reserva.cancelada = True
                reserva.save()

                EmailService.enviar_cancelacion_reserva(reserva)
                
                if reserva.espacio.estado == 'RESERVADO':
                    reserva.espacio.estado = 'LIBRE'
                    reserva.espacio.save()
                    logger.info(f"🔓 Espacio {reserva.espacio.numero} liberado")
                
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
        """Distribución de reservas por hora del día (hoy)"""
        try:
            hoy = timezone.now().date()
            
            reservas = (
                Reserva.objects
                .filter(fecha=hoy)
                .annotate(hora_del_dia=ExtractHour('hora'))
                .values('hora_del_dia')
                .annotate(
                    total_reservas=Count('id'),
                    minutos_totales=Sum('duracion')
                )
                .order_by('hora_del_dia')
            )
            
            labels = [f'{h:02d}:00' for h in range(24)]
            reservas_data = [0] * 24
            minutos_data = [0] * 24
            
            for r in reservas:
                h = r['hora_del_dia']
                reservas_data[h] = r['total_reservas']
                minutos_data[h] = r['minutos_totales'] or 0
            
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
        """Ocupación por espacio (últimos 7 días)"""
        try:
            hoy = timezone.now().date()
            hace_7_dias = hoy - timedelta(days=7)
            
            reservas = Reserva.objects.filter(
                fecha__gte=hace_7_dias,
                fecha__lte=hoy
            ).values('espacio__numero').annotate(
                total_reservas=Count('id'),
                minutos_ocupados=Sum('duracion')
            ).order_by('espacio__numero')
            
            total_minutos_disponibles = 7 * 24 * 60
            
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
        """Predicción de demanda por día de la semana (últimos 30 días)"""
        try:
            hoy = timezone.now().date()
            hace_30_dias = hoy - timedelta(days=30)
            
            reservas = (
                Reserva.objects
                .filter(fecha__gte=hace_30_dias, fecha__lte=hoy)
                .annotate(dia_semana=ExtractWeekDay('fecha'))
                .values('dia_semana')
                .annotate(
                    total_reservas=Count('id'),
                    duracion_promedio=Avg('duracion'),
                    espacios_utilizados=Count('espacio', distinct=True)
                )
                .order_by('dia_semana')
            )
            
            dias = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
            
            reservas_data = [0] * 7
            duracion_data = [0] * 7
            espacios_data = [0] * 7
            
            for r in reservas:
                dia_idx = r['dia_semana'] - 1
                reservas_data[dia_idx] = r['total_reservas']
                duracion_data[dia_idx] = round(r['duracion_promedio'] or 0, 1)
                espacios_data[dia_idx] = r['espacios_utilizados']
            
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

    @action(detail=False, methods=['post'], url_path='enviar_reporte')
    def enviar_reporte(self, request):
        """Genera y envía el reporte semanal por email"""
        try:
            from reports.report_service import ReportService
            from reports.pdf_generator import PDFGenerator
            from notifications.email_service import EmailService
            
            reporte_data = ReportService.generar_reporte_semanal()
            
            if not reporte_data:
                return Response({
                    'success': False,
                    'error': 'No se pudieron generar los datos del reporte'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            pdf_buffer = PDFGenerator.generar_reporte_pdf(reporte_data)
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


# ============================================================
# ✅ SENSOR VIEWSET - Recibe datos de la Raspberry Pi
# ============================================================
class SensorViewSet(viewsets.GenericViewSet):
    """
    API para recibir datos de sensores (Raspberry Pi)
    """
    permission_classes = [permissions.AllowAny]
    queryset = EspacioEstacionamiento.objects.none()

    @action(detail=False, methods=['post'], url_path='estado')
    def recibir_datos(self, request):
        """
        Recibe datos de la Raspberry (sensor_data o heartbeat).
        POST /api/sensor/estado/
        """
        global ULTIMO_HEARTBEAT, ULTIMO_ESTADO_ARDUINO, ALERTA_ENVIADA
        
        # ✅ Validar token
        token = request.headers.get('X-Sensor-Token')
        if not token or token != settings.SENSOR_TOKEN:
            return Response({
                'success': False,
                'error': 'Token inválido'
            }, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data
        data_type = data.get('type', 'sensor_data')
        
        try:
            # ============================================================
            # CASO 1: HEARTBEAT de la Raspberry
            # ============================================================
            if data_type == 'heartbeat':
                raspberry_id = data.get('raspberry_id', 'unknown')
                timestamp = data.get('timestamp', datetime.now().isoformat())
                
                # ✅ Guardar último heartbeat
                ULTIMO_HEARTBEAT[raspberry_id] = timestamp
                
                # ✅ Guardar estado del Arduino
                arduino_info = data.get('arduino', {})
                ULTIMO_ESTADO_ARDUINO[raspberry_id] = {
                    'conectado': arduino_info.get('conectado', False),
                    'ultimo_dato': arduino_info.get('ultimo_dato', timestamp)
                }
                
                logger.info(f"💓 Heartbeat recibido de {raspberry_id} | Arduino: {'✅' if arduino_info.get('conectado') else '❌'}")
                
                # ✅ Si el Arduino está desconectado, enviar alerta (solo una vez)
                if not arduino_info.get('conectado', True):
                    self._enviar_alerta_arduino(raspberry_id)
                else:
                    # Resetear alerta si volvió a conectar
                    if raspberry_id in ALERTA_ENVIADA:
                        ALERTA_ENVIADA[raspberry_id]['arduino'] = False
                
                return Response({
                    'success': True,
                    'mensaje': f'Heartbeat recibido de {raspberry_id}'
                })
            
            # ============================================================
            # CASO 2: DATOS DE SENSOR
            # ============================================================
            elif data_type == 'sensor_data':
                sensor_id = int(data.get('id', 0))
                estado = data.get('estado', '').upper()
                timestamp = data.get('timestamp', datetime.now().isoformat())
                
                if not sensor_id or not estado:
                    return Response({
                        'success': False,
                        'error': 'Faltan campos: id y estado son requeridos'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # ✅ Actualizar estado del espacio
                self._actualizar_espacio(sensor_id, estado)
                
                logger.info(f"📡 Sensor {sensor_id} → {estado}")
                
                return Response({
                    'success': True,
                    'mensaje': f'Sensor {sensor_id} actualizado: {estado}',
                    'data': {
                        'sensor_id': sensor_id,
                        'estado': estado,
                        'timestamp': timestamp
                    }
                })
            
            else:
                return Response({
                    'success': False,
                    'error': f'Tipo de dato no reconocido: {data_type}'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"❌ Error en sensor/estado: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _actualizar_espacio(self, sensor_id, estado):
        """Actualiza el estado del espacio en la base de datos"""
        try:
            espacio, created = EspacioEstacionamiento.objects.get_or_create(
                numero=sensor_id,
                defaults={'estado': estado, 'sensor_conectado': True}
            )
            
            if not created:
                espacio.estado = estado
                espacio.sensor_conectado = True
                espacio.ultimo_heartbeat = timezone.now()
                espacio.save()
            
            # ✅ Si es LIBRE y hay una reserva espontánea activa, liberarla
            if estado == 'LIBRE':
                reserva_espontanea = Reserva.objects.filter(
                    espacio=espacio,
                    cancelada=False,
                    tipo='espontanea'
                ).first()
                if reserva_espontanea:
                    reserva_espontanea.cancelada = True
                    reserva_espontanea.save()
                    logger.info(f"🔓 Reserva espontánea {reserva_espontanea.id} liberada")
            
        except Exception as e:
            logger.error(f"❌ Error actualizando espacio {sensor_id}: {e}")
    
    def _enviar_alerta_arduino(self, raspberry_id):
        """Envía alerta por Telegram cuando el Arduino está desconectado (solo una vez)"""
        global ALERTA_ENVIADA
        
        # ✅ Evitar spam: solo enviar una vez
        if raspberry_id in ALERTA_ENVIADA and ALERTA_ENVIADA[raspberry_id].get('arduino', False):
            return
        
        try:
            ultimo_dato = ULTIMO_ESTADO_ARDUINO.get(raspberry_id, {}).get('ultimo_dato', 'N/A')
            
            mensaje = f"""
⚠️ ALERTA DEL SISTEMA

El Arduino está desconectado.

📍 Raspberry Pi: {raspberry_id}
⏱️ Último dato recibido: {ultimo_dato}

Acción recomendada: Verificar conexión USB entre Arduino y Raspberry Pi.
"""
            TelegramService.enviar_alerta_administrador(mensaje)
            
            # ✅ Marcar alerta como enviada
            if raspberry_id not in ALERTA_ENVIADA:
                ALERTA_ENVIADA[raspberry_id] = {'arduino': False, 'raspberry': False}
            ALERTA_ENVIADA[raspberry_id]['arduino'] = True
            
            logger.info(f"📨 Alerta Arduino enviada para {raspberry_id}")
        except Exception as e:
            logger.error(f"❌ Error enviando alerta Arduino: {e}")