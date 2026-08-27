# core/services.py
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from django.utils.timezone import localtime
from django.db import models
from .models import EspacioEstacionamiento, Reserva, Feriado
from notifications.email_service import EmailService
from notifications.telegram_service import TelegramService
import logging
import datetime as dt

logger = logging.getLogger(__name__)


class ReservaService:
    """Servicio para gestionar reservas"""
    
    @staticmethod
    def calcular_hora_fin(hora_inicio, duracion_minutos):
        """Calcula la hora de fin sumando la duración"""
        try:
            if isinstance(hora_inicio, str):
                hora_inicio = datetime.strptime(hora_inicio, '%H:%M:%S').time()
            
            # Quitar microsegundos si existen
            if hasattr(hora_inicio, 'microsecond'):
                hora_inicio = hora_inicio.replace(microsecond=0)
            
            base = datetime.combine(datetime.today(), hora_inicio)
            hora_fin = base + timedelta(minutes=duracion_minutos)
            return hora_fin.time().replace(microsecond=0)
        except Exception as e:
            logger.error(f"Error calculando hora fin: {e}")
            raise ValueError(f"Error calculando hora fin: {e}")
    
    # ============================================================
    # VALIDACIONES PARA RESERVAS PROGRAMADAS
    # ============================================================
    @staticmethod
    def validar_horario_programada(fecha, hora):
        """
        Valida que la reserva programada cumpla con:
        - Lunes a Viernes: 8:00 - 20:00
        - Sábados: 8:00 - 12:00
        - Domingos: No se permite
        """
        try:
            dia_semana = fecha.weekday()
            
            if isinstance(hora, str):
                hora = datetime.strptime(hora, '%H:%M:%S').time()

            # ✅ Verificar si la fecha es feriado
            if Feriado.objects.filter(fecha=fecha, activo=True).exists():
                return False, "❌ No se permiten reservas en días feriados"    
                
            # Domingo (6) - No permitido
            if dia_semana == 6:
                return False, "❌ Los domingos no se permiten reservas programadas"
            
            # Sábado (5) - Solo 8:00 - 12:00
            if dia_semana == 5:
                if hora < dt.time(8, 0) or hora > dt.time(12, 0):
                    return False, "❌ Los sábados solo se puede reservar de 8:00 a 12:00"
                return True, "✅ Horario válido"
            
            # Lunes a Viernes (0-4) - 8:00 - 20:00
            if dia_semana in [0, 1, 2, 3, 4]:
                if hora < dt.time(8, 0) or hora > dt.time(20, 0):
                    return False, "❌ De Lunes a Viernes solo se puede reservar de 8:00 a 20:00"
                return True, "✅ Horario válido"
            
            return False, "❌ Día no válido para reserva programada"
            
        except Exception as e:
            logger.error(f"Error validando horario: {e}")
            return False, f"❌ Error validando horario: {e}"
    
    @staticmethod
    def validar_antelacion(fecha, hora):
        """
        Valida que la reserva sea al menos 1 hora después de la hora actual
        SOLO para reservas programadas
        """
        try:
            # ✅ Usar hora local (Argentina)
            ahora = localtime(timezone.now())
            fecha_hoy = ahora.date()
            hora_actual = ahora.time()
            
            if isinstance(fecha, str):
                fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
            
            if isinstance(hora, str):
                hora = datetime.strptime(hora, '%H:%M:%S').time()
            
            logger.info(f"🔍 Validando antelación - Fecha: {fecha}, Hoy: {fecha_hoy}")
            
            # Solo validar si la reserva es para hoy
            if fecha == fecha_hoy:
                hora_minima = (ahora + timedelta(hours=1)).time()
                if hora < hora_minima:
                    return False, f"❌ La reserva debe ser al menos 1 hora después de la hora actual (mínimo {hora_minima.strftime('%H:%M')})"
                return True, "✅ Antelación válida"
            
            return True, "✅ Antelación válida (día futuro)"
            
        except Exception as e:
            logger.error(f"Error validando antelación: {e}")
            return False, f"❌ Error validando antelación: {e}"
    
    # ============================================================
    # LIBERACIÓN DE RESERVAS VENCIDAS (PROGRAMADAS Y ESPONTÁNEAS)
    # ============================================================
    @staticmethod
    def liberar_reservas_vencidas():
        """
        Libera espacios que tienen reservas (programadas o espontáneas)
        que ya pasaron la hora de fin.
        """
        try:
            # ✅ Usar hora local (Argentina)
            ahora = localtime(timezone.now())
            fecha_hoy = ahora.date()
            hora_actual = ahora.time()
            
            # ✅ Liberar TODAS las reservas (programadas Y espontáneas)
            # que ya pasaron la hora de fin
            reservas_vencidas = Reserva.objects.filter(
                cancelada=False,
                fecha__lt=fecha_hoy
            )
            
            reservas_vencidas_hoy = Reserva.objects.filter(
                cancelada=False,
                fecha=fecha_hoy,
                hora_fin__lt=hora_actual
            )
            
            reservas_vencidas = reservas_vencidas | reservas_vencidas_hoy
            
            espacios_liberados = 0
            
            for reserva in reservas_vencidas:
                with transaction.atomic():
                    reserva.cancelada = True
                    reserva.save()
                    
                    # Si el espacio está reservado, liberarlo
                    if reserva.espacio.estado == 'RESERVADO':
                        reserva.espacio.estado = 'LIBRE'
                        reserva.espacio.save()
                        espacios_liberados += 1
                        logger.info(f"🔓 Espacio {reserva.espacio.numero} liberado (reserva {reserva.id} vencida - tipo: {reserva.tipo})")
            
            if espacios_liberados > 0:
                logger.info(f"✅ {espacios_liberados} espacios liberados por reservas vencidas")
            
            return espacios_liberados
            
        except Exception as e:
            logger.error(f"Error liberando reservas vencidas: {e}")
            return 0
    
    # ============================================================
    # VERIFICAR DISPONIBILIDAD
    # ============================================================
    @staticmethod
    def verificar_disponibilidad(espacio_numero, fecha, hora_inicio, duracion):
        """
        Verifica si un espacio está disponible para reservar en una fecha/hora específica.
        """
        try:
            # Liberar reservas vencidas (programadas Y espontáneas)
            ReservaService.liberar_reservas_vencidas()
            
            try:
                espacio = EspacioEstacionamiento.objects.get(numero=espacio_numero)
            except EspacioEstacionamiento.DoesNotExist:
                return False, f"El espacio {espacio_numero} no existe", None
            
            if isinstance(hora_inicio, str):
                hora_inicio = datetime.strptime(hora_inicio, '%H:%M:%S').time()
            
            hora_fin = ReservaService.calcular_hora_fin(hora_inicio, duracion)
            
            # ✅ Usar hora local para comparaciones
            ahora = localtime(timezone.now())
            fecha_hoy = ahora.date()
            hora_actual = ahora.time()
            
            # CASO 1: Reserva para HOY
            if fecha == fecha_hoy:
                # Si el espacio está OCUPADO físicamente
                if espacio.estado == 'OCUPADO':
                    if hora_inicio <= hora_actual:
                        return False, "❌ El espacio está ocupado físicamente en este momento", None
                
                # Si el espacio está RESERVADO (por otra reserva)
                if espacio.estado == 'RESERVADO':
                    reservas_activas = Reserva.objects.filter(
                        espacio=espacio,
                        cancelada=False,
                        fecha=fecha_hoy
                    )
                    
                    conflictos = reservas_activas.filter(
                        models.Q(hora__lt=hora_fin) & models.Q(hora_fin__gt=hora_inicio)
                    )
                    
                    if conflictos.exists():
                        return False, "❌ El espacio ya está reservado en ese horario", conflictos
            
            # CASO 2: Reserva para OTRO DÍA
            # Buscar conflictos con otras reservas en la misma fecha/hora
            conflictos = Reserva.objects.filter(
                espacio__numero=espacio_numero,
                fecha=fecha,
                cancelada=False
            ).filter(
                models.Q(hora__lt=hora_fin) & models.Q(hora_fin__gt=hora_inicio)
            )
            
            if conflictos.exists():
                return False, "❌ El espacio no está disponible en ese horario", conflictos
            
            return True, "✅ Espacio disponible", None
            
        except Exception as e:
            logger.error(f"Error verificando disponibilidad: {e}")
            return False, f"Error en la verificación: {str(e)}", None
    
    # ============================================================
    # CREAR RESERVA (SEPARADA POR TIPO)
    # ============================================================
    @staticmethod
    def crear_reserva(data, usuario=None):
        """
        Crea una nueva reserva con todas las validaciones.
        Lógica separada para reservas programadas y espontáneas.
        """
        try:
            # 1. Validar datos obligatorios
            campos_requeridos = ['espacio_numero', 'fecha', 'hora', 'duracion', 'email', 'telefono']
            for campo in campos_requeridos:
                if campo not in data or not data[campo]:
                    raise ValueError(f"El campo '{campo}' es obligatorio")
            
            # 2. Obtener datos
            espacio_numero = int(data['espacio_numero'])
            fecha = data['fecha']
            hora = data['hora']
            duracion = int(data['duracion'])
            tipo = data.get('tipo', 'programada')
            
            # 3. Obtener espacio
            try:
                espacio = EspacioEstacionamiento.objects.get(numero=espacio_numero)
            except EspacioEstacionamiento.DoesNotExist:
                raise ValueError(f"El espacio {espacio_numero} no existe")
            
            # ============================================================
            # LÓGICA PARA RESERVA PROGRAMADA
            # ============================================================
            if tipo == 'programada':
                # Validar días y horarios permitidos
                valido, mensaje = ReservaService.validar_horario_programada(fecha, hora)
                if not valido:
                    raise ValueError(mensaje)
                
                # Validar antelación (1 hora después) - ahora usa localtime
                valido, mensaje = ReservaService.validar_antelacion(fecha, hora)
                if not valido:
                    raise ValueError(mensaje)
                
                # Calcular hora fin
                hora_fin = ReservaService.calcular_hora_fin(hora, duracion)
                
                # Verificar disponibilidad
                disponible, mensaje, conflictos = ReservaService.verificar_disponibilidad(
                    espacio_numero, fecha, hora, duracion
                )
                if not disponible:
                    raise ValueError(mensaje)
                
                # Crear reserva programada
                with transaction.atomic():
                    reserva = Reserva.objects.create(
                        espacio=espacio,
                        usuario=usuario,
                        usuario_nombre=data.get('usuario_nombre', usuario.username if usuario else ''),
                        email=data['email'],
                        telefono=data['telefono'],
                        fecha=fecha,
                        hora=hora,
                        hora_fin=hora_fin,
                        duracion=duracion,
                        patente=data.get('patente', ''),
                        tipo=tipo
                    )
                    
                    espacio.estado = 'RESERVADO'
                    espacio.save()
                    
                    EmailService.enviar_confirmacion_reserva(reserva)
                    TelegramService.enviar_confirmacion_reserva(reserva)
                    
                    logger.info(f"✅ Reserva PROGRAMADA {reserva.id} creada - Espacio {espacio_numero}")
                    return reserva
            
            # ============================================================
            # LÓGICA PARA RESERVA ESPONTÁNEA
            # ============================================================
            elif tipo == 'espontanea':
                # ✅ Las espontáneas NO tienen validaciones de horario ni antelación
                
                # ✅ Verificar si la fecha es feriado
                if Feriado.objects.filter(fecha=fecha, activo=True).exists():
                    return False, "❌ No se permiten reservas en días feriados"

                # Verificar disponibilidad (el espacio debe estar LIBRE en este momento)
                if espacio.estado != 'LIBRE':
                    raise ValueError("❌ El espacio no está disponible para reserva espontánea")
                
                # ✅ Calcular hora de inicio = ahora (CON ZONA HORARIA LOCAL)
                ahora = localtime(timezone.now())
                hora_actual = ahora.time()
                fecha_actual = ahora.date()
                
                # ✅ Verificar que no haya una reserva espontánea activa para este espacio
                reserva_activa = Reserva.objects.filter(
                    espacio=espacio,
                    cancelada=False,
                    tipo='espontanea'
                ).first()
                
                if reserva_activa:
                    raise ValueError("❌ Ya hay una reserva espontánea activa para este espacio")
                
                # ✅ Calcular hora_fin (hora actual + duración)
                hora_fin = ReservaService.calcular_hora_fin(hora_actual, duracion)
                
                # ✅ Crear reserva espontánea con fecha y hora actual
                with transaction.atomic():
                    reserva = Reserva.objects.create(
                        espacio=espacio,
                        usuario=usuario,
                        usuario_nombre=data.get('usuario_nombre', 'Usuario Espontáneo'),
                        email=data.get('email', f'espontaneo_{int(datetime.now().timestamp())}@smartparking.com'),
                        telefono=data['telefono'],
                        fecha=fecha_actual,
                        hora=hora_actual,
                        hora_fin=hora_fin,
                        duracion=duracion,
                        patente=data.get('patente', ''),
                        tipo=tipo
                    )
                    
                    # ✅ El espacio pasa a RESERVADO
                    espacio.estado = 'RESERVADO'
                    espacio.save()
                    
                    # ✅ Notificaciones
                    EmailService.enviar_confirmacion_reserva(reserva)
                    TelegramService.enviar_confirmacion_reserva(reserva)
                    
                    logger.info(f"✅ Reserva ESPONTÁNEA {reserva.id} creada - Espacio {espacio_numero}")
                    return reserva
            
            else:
                raise ValueError(f"❌ Tipo de reserva no válido: {tipo}")
                
        except Exception as e:
            logger.error(f"Error creando reserva: {e}")
            raise