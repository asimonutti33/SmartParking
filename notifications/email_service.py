# notifications/email_service.py
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para enviar correos electrónicos"""
    
    @staticmethod
    def enviar_confirmacion_reserva(reserva):
        """
        Envía email de confirmación de reserva al usuario
        """
        try:
            # Construir contexto para la plantilla
            context = {
                'reserva': reserva,
                'espacio_numero': reserva.espacio.numero,
                'usuario_nombre': reserva.usuario_nombre or 'Usuario',
                'fecha': reserva.fecha.strftime('%d/%m/%Y'),
                'hora': reserva.hora.strftime('%H:%M'),
                'hora_fin': reserva.hora_fin.strftime('%H:%M'),
                'duracion': reserva.duracion,
                'patente': reserva.patente or 'No especificada',
                'tipo': dict(reserva.TIPOS).get(reserva.tipo, reserva.tipo),
                'telefono': reserva.telefono,
                'email': reserva.email,
            }
            
            # Renderizar plantilla HTML
            html_message = render_to_string('emails/confirmacion_reserva.html', context)
            plain_message = strip_tags(html_message)
            
            # Enviar email
            subject = f'✅ Reserva confirmada - Espacio {reserva.espacio.numero}'
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[reserva.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"📧 Email de confirmación enviado a {reserva.email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando email: {e}")
            return False
    
    @staticmethod
    def enviar_cancelacion_reserva(reserva):
        """
        Envía email de cancelación de reserva al usuario
        """
        try:
            context = {
                'reserva': reserva,
                'espacio_numero': reserva.espacio.numero,
                'usuario_nombre': reserva.usuario_nombre or 'Usuario',
                'fecha': reserva.fecha.strftime('%d/%m/%Y'),
                'hora': reserva.hora.strftime('%H:%M'),
            }
            
            html_message = render_to_string('emails/cancelacion_reserva.html', context)
            plain_message = strip_tags(html_message)
            
            subject = f'❌ Reserva cancelada - Espacio {reserva.espacio.numero}'
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[reserva.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"📧 Email de cancelación enviado a {reserva.email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando email de cancelación: {e}")
            return False
    
    # ============================================================
    # ✅ NUEVO: Enviar Reporte Semanal (DENTRO de la clase)
    # ============================================================
    @staticmethod
    def enviar_reporte_semanal(reporte_data, pdf_buffer):
        """
        Envía el reporte semanal por email con PDF adjunto
        """
        try:
            # Validar datos
            if not reporte_data:
                logger.error("❌ reporte_data vacío")
                return False
            
            if not pdf_buffer:
                logger.error("❌ pdf_buffer vacío")
                return False
            
            # Construir asunto
            subject = f"📊 Reporte Semanal - {reporte_data['periodo']['inicio']} al {reporte_data['periodo']['fin']}"
            
            # Cuerpo del mensaje (texto plano)
            mensaje = f"""
📊 Reporte Semanal de Reservas - Smart Parking Rafaela

Período: {reporte_data['periodo']['inicio']} al {reporte_data['periodo']['fin']}
Generado: {reporte_data['fecha_generacion']}

📈 Resumen Ejecutivo:
• Total reservas: {reporte_data['resumen']['total_reservas']}
• Total minutos: {reporte_data['resumen']['total_minutos']}
• Espacios utilizados: {reporte_data['resumen']['espacios_utilizados']}
• Duración promedio: {reporte_data['resumen']['duracion_promedio']} min

🔥 Día pico: {reporte_data['insights']['dia_pico']}
💤 Día valle: {reporte_data['insights']['dia_valle']}
🏆 Espacio Principal: Espacio {reporte_data['insights']['espacio_mas_demandado']}
📊 Ocupación promedio: {reporte_data['insights']['ocupacion_promedio']}%

💡 Recomendaciones:
{chr(10).join(['• ' + r for r in reporte_data['recomendaciones']])}

---
Este reporte ha sido generado automáticamente.
Smart Parking Rafaela
"""
            
            # Destinatario (con valor por defecto)
            to_email = getattr(settings, 'REPORT_EMAIL', 'ale_s33@hotmail.com')
            
            logger.info(f"📧 Enviando reporte a: {to_email}")
            
            # Crear email con adjunto
            email = EmailMessage(
                subject=subject,
                body=mensaje,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email],
            )
            
            # Adjuntar PDF
            pdf_buffer.seek(0)
            pdf_content = pdf_buffer.read()
            
            if not pdf_content:
                logger.error("❌ PDF vacío")
                return False
            
            email.attach(
                f"reporte_semanal_{reporte_data['periodo']['fin'].replace('/', '')}.pdf",
                pdf_content,
                'application/pdf'
            )
            
            email.send(fail_silently=False)
            
            logger.info(f"✅ Reporte semanal enviado a {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando reporte: {e}")
            return False
