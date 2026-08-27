# reports/report_service.py
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.timezone import localtime
from django.db.models import Count, Sum, Avg
from core.models import Reserva
import logging

logger = logging.getLogger(__name__)


class ReportService:
    """Servicio para generar reportes"""
    
    @staticmethod
    def generar_reporte_semanal():
        """
        Genera los datos para el reporte semanal
        Alineado con la semana actual (Lunes a Sábado)
        """
        try:
            hoy = timezone.now().date()
            
            # ============================================================
            # ✅ CALCULAR INICIO DE SEMANA (LUNES)
            # ============================================================
            dia_semana_hoy = hoy.weekday()  # 0=Lunes, 6=Domingo
            
            # Si es Domingo (6), empezar desde el Lunes anterior
            if dia_semana_hoy == 6:
                inicio_semana = hoy - timedelta(days=6)  # Lunes
            else:
                inicio_semana = hoy - timedelta(days=dia_semana_hoy)  # Lunes de esta semana
            
            fin_semana = inicio_semana + timedelta(days=6)  # Domingo
            
            logger.info(f"📅 Semana: {inicio_semana} - {fin_semana}")
            
            # ============================================================
            # 1. MÉTRICAS GENERALES
            # ============================================================
            reservas = Reserva.objects.filter(
                fecha__gte=inicio_semana,
                fecha__lte=fin_semana
            )
            
            total_reservas = reservas.count()
            total_minutos = reservas.aggregate(Sum('duracion'))['duracion__sum'] or 0
            espacios_utilizados = reservas.values('espacio').distinct().count()
            duracion_promedio = reservas.aggregate(Avg('duracion'))['duracion__avg'] or 0
            
            # ============================================================
            # 2. DISTRIBUCIÓN POR DÍA (LUNES A SÁBADO)
            # ============================================================
            dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
            distribucion_dias = []
            
            for i in range(6):  # Lunes a Sábado
                fecha = inicio_semana + timedelta(days=i)
                reservas_dia = reservas.filter(fecha=fecha)
                distribucion_dias.append({
                    'dia': dias_nombres[i],
                    'fecha': fecha.strftime('%d/%m/%Y'),
                    'reservas': reservas_dia.count(),
                    'minutos': reservas_dia.aggregate(Sum('duracion'))['duracion__sum'] or 0
                })
            
            # ============================================================
            # 3. TOP 3 ESPACIOS
            # ============================================================
            top_espacios = reservas.values('espacio__numero').annotate(
                total_reservas=Count('id'),
                minutos_ocupados=Sum('duracion')
            ).order_by('-total_reservas')[:3]
            
            total_minutos_disponibles = 6 * 24 * 60  # 6 días * 24h * 60min
            
            for espacio in top_espacios:
                minutos = espacio['minutos_ocupados'] or 0
                espacio['porcentaje'] = round((minutos / total_minutos_disponibles) * 100, 2)
            
            # ============================================================
            # 4. INSIGHTS
            # ============================================================
            if distribucion_dias:
                dia_pico = max(distribucion_dias, key=lambda x: x['reservas'])
                dia_valle = min(distribucion_dias, key=lambda x: x['reservas'])
            else:
                dia_pico = {'dia': 'Sin datos', 'reservas': 0}
                dia_valle = {'dia': 'Sin datos', 'reservas': 0}
            
            espacio_mas_demandado = top_espacios[0] if top_espacios else None
            
            ocupacion_promedio = round(
                (total_minutos / (espacios_utilizados or 1) / total_minutos_disponibles) * 100, 2
            ) if espacios_utilizados > 0 else 0
            
            # ============================================================
            # 5. RECOMENDACIONES
            # ============================================================
            recomendaciones = []
            
            if dia_pico['reservas'] > 0 and dia_pico['dia'] != 'Sin datos':
                recomendaciones.append(
                    f"🔥 El {dia_pico['dia']} es el día con mayor demanda "
                    f"({dia_pico['reservas']} reservas). Considere aumentar personal "
                    f"o habilitar espacios adicionales para ese día."
                )
            else:
                recomendaciones.append(
                    f"📊 No hay suficientes datos para identificar días pico."
                )
            
            if dia_valle['reservas'] == 0 and dia_valle['dia'] != 'Sin datos':
                recomendaciones.append(
                    f"💤 El {dia_valle['dia']} tiene baja demanda. "
                    f"Ideal para realizar mantenimiento o limpieza."
                )
            
            if espacio_mas_demandado:
                recomendaciones.append(
                    f"🏆 El Espacio {espacio_mas_demandado['espacio__numero']} es el más demandado "
                    f"({espacio_mas_demandado['total_reservas']} reservas)."
                )
            
            if total_reservas == 0:
                recomendaciones.append(
                    f"📊 No hay reservas registradas en la semana. "
                    f"Considere estrategias de promoción."
                )
            elif ocupacion_promedio > 50:
                recomendaciones.append(
                    f"📊 Ocupación promedio del {ocupacion_promedio}%. Alta capacidad."
                )
            elif ocupacion_promedio < 20:
                recomendaciones.append(
                    f"📊 Ocupación promedio del {ocupacion_promedio}%. "
                    f"Considere estrategias de promoción."
                )
            else:
                recomendaciones.append(
                    f"📊 Ocupación promedio del {ocupacion_promedio}%. "
                    f"Parámetros normales."
                )
            
            # ============================================================
            # 6. ARMAR ESTRUCTURA DEL REPORTE
            # ============================================================
            return {
                'periodo': {
                    'inicio': inicio_semana.strftime('%d/%m/%Y'),
                    'fin': fin_semana.strftime('%d/%m/%Y')
                },
                'fecha_generacion': localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S'),
                'resumen': {
                    'total_reservas': total_reservas,
                    'total_minutos': total_minutos,
                    'espacios_utilizados': espacios_utilizados or 0,
                    'duracion_promedio': round(duracion_promedio, 1)
                },
                'distribucion_dias': distribucion_dias,
                'top_espacios': top_espacios,
                'insights': {
                    'dia_pico': dia_pico['dia'] if dia_pico['reservas'] > 0 else 'Sin datos',
                    'dia_valle': dia_valle['dia'] if dia_valle['reservas'] > 0 else 'Sin datos',
                    'espacio_mas_demandado': espacio_mas_demandado['espacio__numero'] if espacio_mas_demandado else 'N/A',
                    'ocupacion_promedio': ocupacion_promedio
                },
                'recomendaciones': recomendaciones
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}")
            return None