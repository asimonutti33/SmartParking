#!/usr/bin/env python
"""
Script para verificar los heartbeats de las Raspberry Pi.
Usa los datos de la tabla espacios_estacionamiento.
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from notifications.telegram_service import TelegramService
from core.models import EspacioEstacionamiento

TIMEOUT_RASPBERRY = 600  # 10 minutos


def verificar_heartbeats():
    """
    Verifica si la Raspberry está enviando datos.
    Si todos los espacios tienen 'sensor_conectado = False',
    significa que la Raspberry está caída.
    """
    try:
        ahora = timezone.now()
        
        # ✅ Verificar si hay algún espacio conectado
        espacios_conectados = EspacioEstacionamiento.objects.filter(sensor_conectado=True)
        
        # ✅ Si hay algún espacio conectado, la Raspberry está viva
        if espacios_conectados.exists():
            print(f"✅ {datetime.now().strftime('%H:%M:%S')} - Raspberry conectada ({espacios_conectados.count()} sensores activos)")
            
            # ✅ Verificar si algún sensor está caído (solo para logging)
            sensores_caidos = EspacioEstacionamiento.objects.filter(sensor_conectado=False)
            if sensores_caidos.exists():
                for sensor in sensores_caidos:
                    print(f"   ⚠️ Sensor {sensor.numero} caído (última actualización: {sensor.ultima_actualizacion})")
            
            return 0
        
        # ✅ Si NO hay espacios conectados, la Raspberry está caída
        # Buscar el último espacio actualizado para obtener el timestamp
        ultimo_espacio = EspacioEstacionamiento.objects.order_by('-ultima_actualizacion').first()
        
        if ultimo_espacio:
            ultimo_contacto = ultimo_espacio.ultima_actualizacion
            tiempo_sin_contacto = (ahora - ultimo_contacto).total_seconds()
            
            mensaje = f"""
⚠️ ALERTA DEL SISTEMA

La Raspberry Pi está caída o sin conexión.

🆔 Dispositivo: Raspberry Pi (Hub)
⏱️ Último dato recibido: {ultimo_contacto.strftime('%d/%m/%Y %H:%M:%S')}
⏳ Tiempo sin contacto: {int(tiempo_sin_contacto)} segundos

Acción recomendada: Verificar conexión a Internet y estado de la Raspberry Pi.
"""
            TelegramService.enviar_alerta_administrador(mensaje)
            print(f"📨 Alerta Raspberry enviada")
            return 1
        
        print(f"✅ {datetime.now().strftime('%H:%M:%S')} - No hay datos de sensores")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


if __name__ == "__main__":
    print("=" * 50)
    print("  CHECK HEARTBEATS - Smart Parking")
    print("=" * 50)
    print(f"⏱️  Timeout: {TIMEOUT_RASPBERRY}s")
    print()
    
    verificar_heartbeats()