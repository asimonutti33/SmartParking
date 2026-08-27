#!/usr/bin/env python
"""
Script para verificar los heartbeats de las Raspberry Pi.
Si una Raspberry no ha enviado heartbeat en más de 60 segundos,
envía una alerta por Telegram.
Uso: python scripts/check_heartbeats.py
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# ============================================================
# CONFIGURAR DJANGO
# ============================================================
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# ============================================================
# IMPORTAR DEPENDENCIAS
# ============================================================
from notifications.telegram_service import TelegramService

# Importar variables globales desde views.py
from core.views import ULTIMO_HEARTBEAT, ALERTA_ENVIADA

# ============================================================
# CONFIGURACIÓN
# ============================================================
TIMEOUT_RASPBERRY = 60  # 60 segundos sin heartbeat


def verificar_heartbeats():
    """
    Verifica los heartbeats de todas las Raspberry Pi.
    Si una Raspberry no ha enviado heartbeat en más de 60 segundos,
    envía una alerta por Telegram.
    """
    try:
        ahora = timezone.now()
        alertas_enviadas = 0
        
        # ✅ Iterar sobre todas las Raspberry registradas
        for raspberry_id, timestamp_str in list(ULTIMO_HEARTBEAT.items()):
            # Convertir timestamp a datetime
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str)
            else:
                timestamp = timestamp_str
            
            # Calcular tiempo sin contacto
            tiempo_sin_contacto = (ahora - timestamp).total_seconds()
            
            # ✅ Si la Raspberry no responde
            if tiempo_sin_contacto > TIMEOUT_RASPBERRY:
                # Verificar si ya se envió alerta
                if (raspberry_id not in ALERTA_ENVIADA or 
                    not ALERTA_ENVIADA[raspberry_id].get('raspberry', False)):
                    
                    mensaje = f"""
⚠️ ALERTA DEL SISTEMA

La Raspberry Pi está caída o sin conexión.

🆔 Raspberry ID: {raspberry_id}
⏱️ Último heartbeat: {timestamp.strftime('%d/%m/%Y %H:%M:%S')}
⏳ Tiempo sin contacto: {int(tiempo_sin_contacto)} segundos

Acción recomendada: Verificar conexión a Internet y estado de la Raspberry Pi.
"""
                    TelegramService.enviar_alerta_administrador(mensaje)
                    
                    # ✅ Marcar alerta como enviada
                    if raspberry_id not in ALERTA_ENVIADA:
                        ALERTA_ENVIADA[raspberry_id] = {'arduino': False, 'raspberry': False}
                    ALERTA_ENVIADA[raspberry_id]['raspberry'] = True
                    
                    alertas_enviadas += 1
                    print(f"📨 Alerta Raspberry {raspberry_id} enviada")
            
            # ✅ Si la Raspberry volvió a conectarse, resetear alerta
            else:
                if (raspberry_id in ALERTA_ENVIADA and 
                    ALERTA_ENVIADA[raspberry_id].get('raspberry', False)):
                    ALERTA_ENVIADA[raspberry_id]['raspberry'] = False
                    print(f"✅ Raspberry {raspberry_id} reconectada")
        
        if alertas_enviadas == 0:
            print(f"✅ {datetime.now().strftime('%H:%M:%S')} - Todas las Raspberry están conectadas")
        
        return alertas_enviadas
        
    except Exception as e:
        print(f"❌ Error verificando heartbeats: {e}")
        return 0


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("  CHECK HEARTBEATS - Smart Parking")
    print("=" * 50)
    print(f"⏱️  Timeout: {TIMEOUT_RASPBERRY}s")
    print()
    
    verificar_heartbeats()