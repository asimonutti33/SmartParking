from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from core.models import TelegramUsuario

logger = logging.getLogger(__name__)


@api_view(['POST'])
@csrf_exempt
def telegram_register(request):
    """
    Registra un chat_id de Telegram asociado a un teléfono
    """
    try:
        data = request.data
        telefono = data.get('telefono')
        chat_id = data.get('chat_id')
        
        if not telefono or not chat_id:
            return Response({
                'success': False,
                'error': 'Faltan datos: telefono y chat_id son requeridos'
            }, status=400)
        
        # Normalizar teléfono
        telefono_limpio = ''.join(filter(str.isdigit, telefono))
        
        # Guardar o actualizar
        obj, created = TelegramUsuario.objects.update_or_create(
            telefono=telefono_limpio,
            defaults={'chat_id': chat_id}
        )
        
        return Response({
            'success': True,
            'mensaje': '✅ Usuario registrado correctamente',
            'created': created
        })
        
    except Exception as e:
        logger.error(f"Error registrando usuario: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def telegram_webhook(request):
    """
    Webhook para recibir mensajes de Telegram
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"📩 Webhook recibido: {data}")
            
            # Procesar mensaje
            message = data.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')
            
            if text == '/start':
                # Responder al usuario
                from .telegram_service import TelegramService
                TelegramService.enviar_mensaje(
                    chat_id,
                    "✅ ¡Bienvenido a Smart Parking Rafaela!\n\n"
                    "Para recibir notificaciones de tus reservas, "
                    "regístrate enviando tu número de teléfono:\n\n"
                    "/registrar 3492123456"
                )
            
            elif text.startswith('/registrar'):
                # Extraer teléfono
                partes = text.split()
                if len(partes) >= 2:
                    telefono = partes[1]
                    # Guardar en base de datos
                    TelegramUsuario.objects.update_or_create(
                        chat_id=chat_id,
                        defaults={'telefono': telefono}
                    )
                    from .telegram_service import TelegramService
                    TelegramService.enviar_mensaje(
                        chat_id,
                        f"✅ ¡Registro completado!\nTeléfono: {telefono}\n"
                        "Ahora recibirás notificaciones de tus reservas."
                    )
            
            return HttpResponse(status=200)
            
        except Exception as e:
            logger.error(f"Error en webhook: {e}")
            return HttpResponse(status=500)
    
    return HttpResponse(status=405)
