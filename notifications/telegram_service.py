import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramService:
    """
    Servicio para enviar mensajes por Telegram
    """
    
    # ✅ TOKEN DEL BOT
    BOT_TOKEN = "8223297017:AAEnupeHaQ8ecCyZM3G9E4dEVRwwK4bsutA"
    BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
    
    # ✅ CHAT ID DEL ADMINISTRADOR (el que usabas en Node-RED)
    ADMIN_CHAT_ID = "5164929345"
    
    @staticmethod
    def enviar_mensaje(chat_id, texto, parse_mode='HTML'):
        """
        Envía un mensaje a un chat de Telegram
        """
        try:
            url = f"{TelegramService.BASE_URL}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': texto,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            response = requests.post(url, json=payload, timeout=10)
            data = response.json()
            
            if data.get('ok'):
                logger.info(f"✅ Mensaje enviado a chat {chat_id}")
                return True
            else:
                logger.error(f"❌ Error Telegram: {data}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje: {e}")
            return False
    
    @staticmethod
    def obtener_chat_id():
        """
        Obtiene el chat_id del administrador.
        Útil para pruebas.
        """
        try:
            url = f"{TelegramService.BASE_URL}/getUpdates"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('ok') and data.get('result'):
                # Tomar el primer mensaje
                chat_id = data['result'][0]['message']['chat']['id']
                logger.info(f"✅ Chat ID encontrado: {chat_id}")
                return chat_id
            else:
                logger.warning("⚠️ No hay mensajes. Envía un mensaje al bot primero.")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo chat_id: {e}")
            return None
    
    @staticmethod
    def enviar_confirmacion_reserva(reserva):
        """
        Envía confirmación de reserva al usuario por Telegram
        """
        try:
            from core.models import TelegramUsuario
            
            telefono = reserva.telefono
            telefono_limpio = ''.join(filter(str.isdigit, telefono))
            
            # Buscar chat_id
            try:
                telegram_user = TelegramUsuario.objects.get(telefono__contains=telefono_limpio)
                chat_id = telegram_user.chat_id
            except TelegramUsuario.DoesNotExist:
                # Intentar sin código de país
                if telefono_limpio.startswith('54'):
                    telefono_sin_pais = telefono_limpio[2:]
                    try:
                        telegram_user = TelegramUsuario.objects.get(telefono__contains=telefono_sin_pais)
                        chat_id = telegram_user.chat_id
                    except TelegramUsuario.DoesNotExist:
                        logger.warning(f"⚠️ Usuario no registrado en Telegram: {telefono}")
                        return False
                else:
                    logger.warning(f"⚠️ Usuario no registrado en Telegram: {telefono}")
                    return False
            
            # Construir mensaje
            mensaje = f"""
<b>✅ Reserva Confirmada</b>

📍 <b>Espacio:</b> #{reserva.espacio.numero}
👤 <b>Usuario:</b> {reserva.usuario_nombre or 'No especificado'}
📅 <b>Fecha:</b> {reserva.fecha.strftime('%d/%m/%Y')}
⏰ <b>Hora:</b> {reserva.hora.strftime('%H:%M')}
🏁 <b>Hora fin:</b> {reserva.hora_fin.strftime('%H:%M')}
⏱️ <b>Duración:</b> {reserva.duracion} minutos
{'🚗 <b>Patente:</b> ' + reserva.patente if reserva.patente else ''}
📋 <b>Tipo:</b> {dict(reserva.TIPOS).get(reserva.tipo, reserva.tipo)}

📞 <b>Teléfono:</b> {reserva.telefono}
📧 <b>Email:</b> {reserva.email}

¡Gracias por utilizar Smart Parking Rafaela! 🚗
"""
            
            return TelegramService.enviar_mensaje(chat_id, mensaje)
            
        except Exception as e:
            logger.error(f"❌ Error enviando confirmación Telegram: {e}")
            return False
    
    @staticmethod
    def enviar_cancelacion_reserva(reserva):
        """
        Envía notificación de cancelación al usuario por Telegram
        """
        try:
            from core.models import TelegramUsuario
            
            telefono = reserva.telefono
            telefono_limpio = ''.join(filter(str.isdigit, telefono))
            
            try:
                telegram_user = TelegramUsuario.objects.get(telefono__contains=telefono_limpio)
                chat_id = telegram_user.chat_id
            except TelegramUsuario.DoesNotExist:
                if telefono_limpio.startswith('54'):
                    telefono_sin_pais = telefono_limpio[2:]
                    try:
                        telegram_user = TelegramUsuario.objects.get(telefono__contains=telefono_sin_pais)
                        chat_id = telegram_user.chat_id
                    except TelegramUsuario.DoesNotExist:
                        return False
                else:
                    return False
            
            mensaje = f"""
<b>❌ Reserva Cancelada</b>

📍 <b>Espacio:</b> #{reserva.espacio.numero}
📅 <b>Fecha:</b> {reserva.fecha.strftime('%d/%m/%Y')}
⏰ <b>Hora:</b> {reserva.hora.strftime('%H:%M')}

El espacio ya está disponible para nuevas reservas.

¡Esperamos verte pronto! 🚗
"""
            
            return TelegramService.enviar_mensaje(chat_id, mensaje)
            
        except Exception as e:
            logger.error(f"❌ Error enviando cancelación Telegram: {e}")
            return False
    
    @staticmethod
    def enviar_alerta_administrador(mensaje):
        """
        Envía alerta al administrador del sistema
        """
        try:
            if not TelegramService.ADMIN_CHAT_ID:
                logger.warning("⚠️ ADMIN_CHAT_ID no configurado")
                return False
            
            mensaje_completo = f"""
<b>⚠️ ALERTA DEL SISTEMA</b>

{mensaje}

<i>Smart Parking Rafaela</i>
"""
            return TelegramService.enviar_mensaje(TelegramService.ADMIN_CHAT_ID, mensaje_completo)
            
        except Exception as e:
            logger.error(f"❌ Error enviando alerta: {e}")
            return False