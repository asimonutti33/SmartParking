# notifications/management/commands/iniciar_bot.py
import telebot
from telebot import types
from django.core.management.base import BaseCommand
from core.models import TelegramUsuario  # Ajustá la importación a tu modelo real

TOKEN = "8223297017:AAEnupeHaQ8ecCyZM3G9E4dEVRwwK4bsutA"
bot = telebot.TeleBot(TOKEN)

class Command(BaseCommand):
    help = "Inicia el bot de Telegram para escuchar comandos y registrar usuarios"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Bot de Smart Parking iniciado y escuchando..."))
        
        # Eliminar webhooks previos por si las dudas
        bot.remove_webhook()
        
        # Iniciar el bucle infinito de escucha
        bot.infinity_polling()

# 1. Manejar el comando /start
@bot.message_handler(commands=['start'])
def enviar_bienvenida(message):
    chat_id = str(message.chat.id)
    nombre = message.from_user.first_name
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    # Botón nativo para que el usuario comparta su contacto de forma segura
    boton_telefono = types.KeyboardButton(text="📱 Compartir mi número de teléfono", request_contact=True)
    markup.add(boton_telefono)
    
    mensaje_texto = (
        f"¡Hola {nombre}! Bienvenido al sistema de <b>Smart Parking Rafaela</b>. 🚗\n\n"
        "Para poder enviarte las confirmaciones y cancelaciones de tus reservas de estacionamiento, "
        "necesitamos vincular tu cuenta de Telegram con tu número de teléfono.\n\n"
        "Por favor, presioná el botón de abajo para registrarte:"
    )
    
    bot.send_message(chat_id, mensaje_texto, parse_mode="HTML", reply_markup=markup)

# 2. Recibir el contacto telefónico y guardarlo en Django
@bot.message_handler(content_types=['contact'])
def recibir_contacto(message):
    chat_id = str(message.chat.id)
    
    if message.contact is not None:
        telefono = message.contact.phone_number  # Ej: 543492XXXXXX
        # Normalizar: quitar el signo '+' si Telegram lo incluye
        telefono_limpio = telefono.replace("+", "")
        
        # Guardar o actualizar en la base de datos de Django
        usuario_telegram, created = TelegramUsuario.objects.update_or_create(
            chat_id=chat_id,
            defaults={'telefono': telefono_limpio}
        )
        
        if created:
            bot.send_message(chat_id, "✅ ¡Registro exitoso! Tu cuenta ha sido vinculada. A partir de ahora recibirás notificaciones de tus reservas acá.", reply_markup=types.ReplyKeyboardRemove())
        else:
            bot.send_message(chat_id, "🔄 Tus datos ya estaban registrados y fueron actualizados correctamente.", reply_markup=types.ReplyKeyboardRemove())
