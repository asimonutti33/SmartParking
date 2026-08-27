import serial
import json
import time
import threading
import logging
import os
import sys
from django.utils.timezone import localtime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from core.models import EspacioEstacionamiento
from django.utils import timezone
from notifications.telegram_service import TelegramService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SerialSensorReader:
    """
    Lee el puerto serie y actualiza la base de datos.
    Incluye reconexión automática.
    """
    
    def __init__(self, port='COM7', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        self.thread = None
        self.contador = 0
        self.ultimo_heartbeat = {}
        self.TIMEOUT_HEARTBEAT = 60
        self._marcar_todos_desconectados()
    
    def _marcar_todos_desconectados(self):
        try:
            actualizados = EspacioEstacionamiento.objects.all().update(sensor_conectado=False)
            print(f"🔌 {actualizados} sensores marcados como desconectados al iniciar")
        except Exception as e:
            print(f"⚠️ Error al marcar sensores: {e}")
    
    def start(self):
        if self.running:
            print("⚠️ El servicio ya está corriendo")
            return
        self.running = True
        self.thread = threading.Thread(target=self._read_loop)
        self.thread.daemon = True
        self.thread.start()
        print(f"✅ Serial Reader iniciado en {self.port} a {self.baudrate} baudios")
    
    def stop(self):
        self.running = False
        if self.serial and self.serial.is_open:
            self.serial.close()
        print("⏹️ Serial Reader detenido")
    
    def _read_loop(self):
        """Bucle principal con reconexión automática"""
        ultima_verificacion = time.time()
        
        while self.running:
            try:
                # Intentar conectar
                self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
                print(f"🔌 Conectado a {self.port}")
                time.sleep(2)
                
                # Bucle de lectura
                while self.running:
                    # Leer datos del serial
                    if self.serial.in_waiting > 0:
                        try:
                            datos = self.serial.readline().decode('utf-8', errors='ignore').strip()
                            if datos:
                                self.contador += 1
                                self._process_data(datos)
                        except Exception as e:
                            print(f"⚠️ Error leyendo datos: {e}")
                            break  # Salir del bucle interno para reconectar
                    
                    # Verificar sensores caídos CADA 5 SEGUNDOS
                    ahora = time.time()
                    if ahora - ultima_verificacion >= 5:
                        ultima_verificacion = ahora
                        self._verificar_sensores_caidos()
                    
                    time.sleep(0.1)
                
                # Si salimos del bucle interno, cerrar conexión
                if self.serial and self.serial.is_open:
                    self.serial.close()
                    print("🔌 Puerto serial cerrado (reconectando...)")
                
                # Esperar antes de reconectar
                time.sleep(2)
                
            except serial.SerialException as e:
                print(f"❌ Error serial: {e} - Reconectando en 5 segundos...")
                self._verificar_sensores_caidos()
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ Error inesperado: {e} - Reconectando en 5 segundos...")
                self._verificar_sensores_caidos()
                time.sleep(5)
    
    def _process_data(self, datos):
        try:
            data = json.loads(datos)
            print(f"📩 [{self.contador}] {data}")
            
            ahora = timezone.now()
            
            if 'heartbeat' in data:
                for sensor_id, estado in data['heartbeat'].items():
                    sensor_id = int(sensor_id)
                    self.ultimo_heartbeat[sensor_id] = ahora
                    self._update_sensor(sensor_id, estado.upper())
                logger.info(f"✅ Heartbeat: {len(data['heartbeat'])} sensores")
            
            elif 'id' in data and 'estado' in data:
                sensor_id = int(data['id'])
                self.ultimo_heartbeat[sensor_id] = ahora
                self._update_sensor(sensor_id, data['estado'].upper())
                logger.info(f"✅ Sensor {data['id']}: {data['estado']}")
            
        except json.JSONDecodeError:
            print(f"⚠️ JSON inválido: {datos}")
        except Exception as e:
            print(f"❌ Error procesando: {e}")
    
    def _update_sensor(self, sensor_id, estado):
        try:
            if estado not in ['LIBRE', 'OCUPADO']:
                return
            
            espacio, created = EspacioEstacionamiento.objects.get_or_create(
                numero=sensor_id,
                defaults={'estado': estado, 'sensor_conectado': True, 'ultimo_heartbeat': timezone.now()}
            )
            if not created:
                espacio.estado = estado
                espacio.sensor_conectado = True
                espacio.ultimo_heartbeat = timezone.now()
                espacio.save()
            print(f"   └─> DB: Sensor {sensor_id} = {estado} (conectado)")
        except Exception as e:
            print(f"❌ Error actualizando DB: {e}")
    
    def _verificar_sensores_caidos(self):
        try:
            ahora = timezone.now()
            alertas = []
            
            for espacio in EspacioEstacionamiento.objects.all():
                sensor_id = espacio.numero
                ultimo = self.ultimo_heartbeat.get(sensor_id)
                
                if ultimo is not None:
                    tiempo_transcurrido = (ahora - ultimo).total_seconds()
                    if tiempo_transcurrido > self.TIMEOUT_HEARTBEAT and espacio.sensor_conectado:
                        espacio.sensor_conectado = False
                        espacio.save()
                        print(f"   ⚠️ Sensor {sensor_id} caído ({int(tiempo_transcurrido)}s)")
                        alertas.append({
                            'id': sensor_id,
                            
                            'ultimo_contacto': localtime(ultimo).strftime('%d/%m/%Y, %H:%M:%S')
                        })
                else:
                    if espacio.sensor_conectado:
                        espacio.sensor_conectado = False
                        espacio.save()
                        print(f"   ⚠️ Sensor {sensor_id} nunca conectado")
                        alertas.append({
                            'id': sensor_id,
                            'ultimo_contacto': 'Nunca conectado'
                        })
            
            if alertas:
                try:
                    mensajes = []
                    for alerta in alertas:
                        mensajes.append(
                            f"⚠️ ALERTA DEL SISTEMA\n"
                            f"Sensor en Espacio #{alerta['id']} dejó de responder.\n"
                            f"Último contacto: {alerta['ultimo_contacto']}\n"
                            f"Acción recomendada: verificar hardware/conexión."
                        )
                    TelegramService.enviar_alerta_administrador("\n\n".join(mensajes))
                except Exception as e:
                    print(f"❌ Error enviando alerta: {e}")
                    
        except Exception as e:
            print(f"❌ Error verificando sensores: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default='COM7')
    parser.add_argument('--baudrate', type=int, default=9600)
    args = parser.parse_args()
    
    reader = SerialSensorReader(port=args.port, baudrate=args.baudrate)
    try:
        reader.start()
        print("\n🔍 Esperando datos del Arduino...\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️ Deteniendo...")
        reader.stop()