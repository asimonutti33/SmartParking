#!/usr/bin/env python
"""
Script para ejecutar el serial reader.
Uso: python manage_serial.py
"""

import os
import sys
import time

if __name__ == "__main__":
    # Configurar Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    from sensors.serial_reader import SerialSensorReader
    
    print("=" * 50)
    print("  SERIAL READER - Smart Parking")
    print("=" * 50)
    print()
    
    # Puerto COM7 para Windows (cambia si es diferente)
    reader = SerialSensorReader(port='COM7', baudrate=9600)
    
    try:
        reader.start()
        print("\n🔍 Esperando datos del Arduino...")
        print("Presiona Ctrl+C para detener\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️ Deteniendo...")
        reader.stop()