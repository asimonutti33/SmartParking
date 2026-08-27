from rest_framework import serializers
from .models import EspacioEstacionamiento, Reserva

class EspacioSerializer(serializers.ModelSerializer):
    disponible = serializers.SerializerMethodField()
    
    class Meta:
        model = EspacioEstacionamiento
        fields = ['id', 'numero', 'estado', 'disponible', 'ultima_actualizacion', 'sensor_conectado']
    
    def get_disponible(self, obj):
        return obj.esta_disponible()


class ReservaSerializer(serializers.ModelSerializer):
    espacio_numero = serializers.IntegerField(source='espacio.numero', read_only=True)
    estado = serializers.SerializerMethodField()
    
    class Meta:
        model = Reserva
        fields = [
            'id', 'espacio', 'espacio_numero', 'usuario', 'usuario_nombre',
            'email', 'telefono', 'fecha', 'hora', 'hora_fin', 'duracion',
            'patente', 'tipo', 'fecha_creacion', 'cancelada', 'estado'
        ]
        read_only_fields = ['hora_fin', 'fecha_creacion']
    
    def get_estado(self, obj):
        return "Cancelada" if obj.cancelada else "Activa"


class CrearReservaSerializer(serializers.Serializer):
    """Serializer para crear reservas"""
    espacio_numero = serializers.IntegerField()
    usuario_nombre = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField()
    telefono = serializers.CharField(max_length=20)
    fecha = serializers.DateField()
    hora = serializers.TimeField()
    duracion = serializers.IntegerField(min_value=1)
    patente = serializers.CharField(required=False, allow_blank=True, max_length=20)
    tipo = serializers.ChoiceField(choices=Reserva.TIPOS, default='programada')