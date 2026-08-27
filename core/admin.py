from django.contrib import admin
from .models import EspacioEstacionamiento, Reserva, Feriado

@admin.register(EspacioEstacionamiento)
class EspacioEstacionamientoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'estado', 'ultima_actualizacion', 'sensor_conectado']
    list_filter = ['estado', 'sensor_conectado']
    search_fields = ['numero']
    readonly_fields = ['ultima_actualizacion', 'ultimo_heartbeat']

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['id', 'espacio', 'usuario_nombre', 'fecha', 'hora', 'estado_reserva']
    list_filter = ['tipo', 'cancelada', 'fecha']
    search_fields = ['usuario_nombre', 'email', 'patente']
    
    def estado_reserva(self, obj):
        return "Cancelada" if obj.cancelada else "Activa"
    estado_reserva.short_description = "Estado"

@admin.register(Feriado)
class FeriadoAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'descripcion', 'activo']
    search_fields = ['descripcion']
    list_filter = ['activo']