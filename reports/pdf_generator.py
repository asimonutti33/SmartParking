# reports/pdf_generator.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Generador de reportes PDF"""
    
    @staticmethod
    def generar_reporte_pdf(reporte_data):
        """
        Genera un PDF a partir de los datos del reporte
        """
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72,
            )
            
            styles = getSampleStyleSheet()
            elements = []
            
            # ============================================================
            # 1. TÍTULO
            # ============================================================
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Title'],
                fontSize=24,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#1a237e')
            )
            elements.append(Paragraph("📊 Reporte Semanal de Reservas", title_style))
            elements.append(Spacer(1, 0.2 * cm))
            
            subtitle_style = ParagraphStyle(
                'SubtitleStyle',
                parent=styles['Normal'],
                fontSize=14,
                alignment=TA_CENTER,
                textColor=colors.grey
            )
            elements.append(Paragraph("Smart Parking Rafaela", subtitle_style))
            elements.append(
                Paragraph(
                    f"Período: {reporte_data['periodo']['inicio']} - {reporte_data['periodo']['fin']}",
                    subtitle_style
                )
            )
            elements.append(
                Paragraph(
                    f"Generado: {reporte_data['fecha_generacion']}",
                    subtitle_style
                )
            )
            elements.append(Spacer(1, 0.5 * cm))
            
            # ============================================================
            # 2. RESUMEN EJECUTIVO
            # ============================================================
            section_style = ParagraphStyle(
                'SectionStyle',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#1a237e')
            )
            elements.append(Paragraph("📈 Resumen Ejecutivo", section_style))
            elements.append(Spacer(1, 0.2 * cm))
            
            resumen = reporte_data['resumen']
            resumen_data = [
                ['Total Reservas', str(resumen['total_reservas'])],
                ['Total Minutos', str(resumen['total_minutos'])],
                ['Espacios Utilizados', str(resumen['espacios_utilizados'])],
                ['Duración Promedio', f"{resumen['duracion_promedio']} min"]
            ]
            
            resumen_table = Table(resumen_data, colWidths=[5*cm, 5*cm])
            resumen_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f2f5')),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('PADDING', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(resumen_table)
            elements.append(Spacer(1, 0.5 * cm))
            
            # ============================================================
            # 3. DISTRIBUCIÓN POR DÍA
            # ============================================================
            elements.append(Paragraph("📅 Distribución por Día", section_style))
            elements.append(Spacer(1, 0.2 * cm))
            
            dias_data = [['Día', 'Fecha', 'Reservas', 'Minutos']]
            for dia in reporte_data['distribucion_dias']:
                bar = '█' * min(dia['reservas'], 20)
                dias_data.append([
                    dia['dia'],
                    dia['fecha'],
                    f"{dia['reservas']}",
                    f"{dia['minutos']} min"
                ])
            
            dias_table = Table(dias_data, colWidths=[3*cm, 3*cm, 4*cm, 3*cm])
            dias_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(dias_table)
            elements.append(Spacer(1, 0.5 * cm))
            
            # ============================================================
            # 4. TOP 3 ESPACIOS
            # ============================================================
            elements.append(Paragraph("🏆 Top 3 Espacios Más Utilizados", section_style))
            elements.append(Spacer(1, 0.2 * cm))
            
            if reporte_data['top_espacios']:
                top_data = [['Espacio', 'Reservas', 'Minutos', '% Ocupación']]
                for espacio in reporte_data['top_espacios']:
                    bar = '█' * min(int(espacio['porcentaje'] / 5), 20)
                    top_data.append([
                        f"#{espacio['espacio__numero']}",
                        str(espacio['total_reservas']),
                        f"{espacio['minutos_ocupados']} min",
                        f"{espacio['porcentaje']}%"
                    ])
                
                top_table = Table(top_data, colWidths=[3*cm, 3*cm, 3*cm, 4*cm])
                top_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff6f00')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('PADDING', (0, 0), (-1, -1), 6),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(top_table)
            else:
                elements.append(Paragraph("No hay datos disponibles", styles['Normal']))
            
            elements.append(Spacer(1, 0.5 * cm))
            
            # ============================================================
            # 5. INSIGHTS Y RECOMENDACIONES
            # ============================================================
            elements.append(Paragraph("💡 Insights y Recomendaciones", section_style))
            elements.append(Spacer(1, 0.2 * cm))
            
            insights = reporte_data['insights']
            insights_data = [
                ['Día pico', insights['dia_pico']],
                ['Día valle', insights['dia_valle']],
                ['Principal espacio', f"Espacio {insights['espacio_mas_demandado']}"],
                ['Ocupación promedio', f"{insights['ocupacion_promedio']}%"]
            ]
            
            insights_table = Table(insights_data, colWidths=[4*cm, 6*cm])
            insights_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3e5f5')),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(insights_table)
            elements.append(Spacer(1, 0.3 * cm))
            
            for rec in reporte_data['recomendaciones']:
                rec_style = ParagraphStyle(
                    'RecStyle',
                    parent=styles['Normal'],
                    fontSize=11,
                    leftIndent=20,
                    textColor=colors.HexColor('#333333')
                )
                elements.append(Paragraph(f"• {rec}", rec_style))
                elements.append(Spacer(1, 0.1 * cm))
            
            elements.append(Spacer(1, 0.5 * cm))
            
            # ============================================================
            # 6. PIE DE PÁGINA
            # ============================================================
            footer_style = ParagraphStyle(
                'FooterStyle',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_CENTER,
                textColor=colors.grey
            )
            elements.append(
                Paragraph(
                    "Reporte generado automáticamente por Smart Parking Rafaela",
                    footer_style
                )
            )
            
            doc.build(elements)
            buffer.seek(0)
            
            logger.info("✅ PDF generado exitosamente")
            return buffer
            
        except Exception as e:
            logger.error(f"❌ Error generando PDF: {e}")
            raise