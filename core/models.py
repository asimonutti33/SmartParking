from django.db import models
from django.contrib.auth.models import User  # <-- Usar el User de Django
from django.utils import timezone

# NOTA: No creamos un modelo Usuario personalizado
# Usamos el User de Django directamente

class EspacioEstacionamiento(models.Model):
    """Modelo para los espacios de estacionamiento"""
    ESTADOS = [
        ('LIBRE', 'Libre'),
        ('OCUPADO', 'Ocupado'),
        ('RESERVADO', 'Reservado'),
        ('DESCONOCIDO', 'Desconocido'),
    ]
    
    numero = models.IntegerField(unique=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='LIBRE')
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    sensor_conectado = models.BooleanField(default=True)
    ultimo_heartbeat = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'espacios_estacionamiento'
        ordering = ['numero']
    
    def __str__(self):
        return f"Espacio {self.numero} - {self.estado}"
    
    def esta_disponible(self):
        return self.estado == 'LIBRE' and self.sensor_conectado


class Reserva(models.Model):
    """Modelo para reservas"""
    TIPOS = [
        ('programada', 'Programada'),
        ('espontanea', 'Espontánea'),
    ]
    
    espacio = models.ForeignKey(EspacioEstacionamiento, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # <-- User de Django
    usuario_nombre = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    telefono = models.CharField(max_length=20)
    fecha = models.DateField()
    hora = models.TimeField()
    hora_fin = models.TimeField()
    duracion = models.IntegerField(help_text="Duración en minutos")
    patente = models.CharField(max_length=20, blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='programada')
    chat_id = models.CharField(max_length=100, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    cancelada = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'reserva'
        ordering = ['fecha', 'hora']
    
    def __str__(self):
        return f"Reserva {self.id} - Espacio {self.espacio.numero} - {self.fecha}"

class TelegramUsuario(models.Model):
    """Vinculación de teléfonos con chat_id de Telegram"""
    telefono = models.CharField(max_length=20, unique=True)
    chat_id = models.CharField(max_length=100, unique=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'telegram'
    
    def __str__(self):
        return f"Telegram: {self.telefono} -> {self.chat_id}"

class Feriado(models.Model):
    fecha = models.DateField(unique=True)
    descripcion = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feriados'
        ordering = ['fecha']

    def __str__(self):
        return f"{self.fecha} - {self.descripcion}"