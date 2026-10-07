# 🚗 Smart Parking - Rafaela

> Sistema de gestión inteligente de estacionamiento con IoT

**Proyecto Final de la carrera Ingeniería en Computación**  
Universidad Nacional de Rafaela (UNRaf) - 2026

## 📋 Descripción

Sistema de estacionamiento inteligente que integra **hardware**, **software embebido** y **servicios en la nube** para optimizar la gestión de espacios de estacionamiento en entornos urbanos.

El proyecto nace como respuesta a la problemática de la congestión vehicular y la dificultad para encontrar estacionamiento disponible, proporcionando una solución tecnológica completa que abarca desde la detección física de vehículos hasta la notificación al usuario final.

**Proyecto desarrollado como Proyecto Final de la carrera de Ingeniería en Computación en la Universidad Nacional de Rafaela (UNRaf).**

---

## ✨ Características

### 🎯 Funcionalidades principales

- ✅ **Monitoreo en tiempo real** de espacios de estacionamiento
- ✅ **Detección física** mediante sensores ultrasónicos HC-SR04
- ✅ **Comunicación IoT** Arduino → Raspberry Pi → Cloud
- ✅ **Sistema de reservas** programadas y espontáneas
- ✅ **Dashboard interactivo** con actualización automática
- ✅ **Notificaciones** por Email y Telegram
- ✅ **Alertas automáticas** por fallos de hardware
- ✅ **Estadísticas** y gráficos interactivos
- ✅ **Forecasting** de demanda
- ✅ **Reportes PDF** semanales automáticos
- ✅ **Gestión de feriados**

### 🔧 Hardware

- **Arduino UNO** con sensores ultrasónicos HC-SR04
- **LEDs RGB** para indicación visual del estado
- **Raspberry Pi** como hub concentrador
- **Comunicación serial USB** entre Arduino y Raspberry

### ☁️ Cloud

- **Backend Django** alojado en VPS
- **PostgreSQL** como base de datos
- **API REST** para comunicación
- **Acceso remoto** vía dominio público

---

## 🏗️ Arquitectura

El sistema está diseñado bajo una **arquitectura en capas**, separando claramente las responsabilidades de cada componente:
┌─────────────────────────────────────────────────────────────────┐
│ CAPA DE PRESENTACIÓN │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ Dashboard Web (HTML + CSS + JavaScript + Chart.js) │ │
│ └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ CAPA DE APLICACIÓN │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ Django REST Framework - API REST │ │
│ │ • /api/sensor/estado/ (Recepción de datos) │ │
│ │ • /api/reservas/ (Gestión de reservas) │ │
│ │ • /api/estadisticas/ (Análisis y estadísticas) │ │
│ └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ CAPA DE NEGOCIO │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ Servicios (Services) │ │
│ │ • ReservaService • ReportService • PDFGenerator │ │
│ │ • EmailService • TelegramService │ │
│ └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ CAPA DE DATOS │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ PostgreSQL │ │
│ │ • espacios_estacionamiento • reserva │ │
│ │ • feriados • telegram │ │
│ └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ CAPA DE HARDWARE │
│ ┌──────────────────────┐ ┌───────────────────────────┐ │
│ │ Arduino UNO │ │ Raspberry Pi 4 │ │
│ │ • Sensores HC-SR04 │────▶│ • Serial Reader │ │
│ │ • LEDs RGB │ USB │ • HTTP Client │ │
│ └──────────────────────┘ └───────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

text

### Flujo de datos
┌─────────────┐ Serial ┌─────────────┐ HTTP ┌─────────────┐
│ Arduino │─────────────▶│ Raspberry │────────────▶│ Cloud │
│ + Sensores │ USB │ Pi (Hub) │ POST │ (Django) │
└─────────────┘ └─────────────┘ └─────────────┘
│
▼
┌─────────────┐
│ PostgreSQL │
└─────────────┘
│
▼
┌─────────────┐
│ Dashboard │
│ Web │
└─────────────┘

text

---

## 🛠️ Stack Tecnológico

### Backend
| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Python** | 3.11 | Lenguaje principal |
| **Django** | 4.2 | Framework web |
| **Django REST Framework** | 3.14 | API REST |
| **PostgreSQL** | 15 | Base de datos |
| **ReportLab** | 4.0 | Generación de PDFs |
| **psycopg2** | 2.9 | Driver PostgreSQL |

### Frontend
| Tecnología | Uso |
|------------|-----|
| **HTML5** | Estructura |
| **CSS3** | Estilos |
| **JavaScript** | Interactividad |
| **Chart.js** | Gráficos interactivos |

### Hardware
| Componente | Uso |
|------------|-----|
| **Arduino UNO** | Microcontrolador |
| **HC-SR04** | Sensores ultrasónicos |
| **LEDs RGB** | Indicadores visuales |
| **Raspberry Pi 4** | Hub concentrador |

### Servicios externos
| Servicio | Uso |
|----------|-----|
| **Gmail SMTP** | Envío de emails |
| **Telegram Bot API** | Notificaciones |
| **DuckDNS** | DNS dinámico |
| **AWS EC2** | VPS en la nube |

---

## 📦 Instalación

### Requisitos previos

- Python 3.10 o superior
- PostgreSQL 15 o superior
- Git
- (Opcional) Arduino IDE
- (Opcional) Raspberry Pi OS

### 1. Clonar el repositorio

```bash
git clone https://github.com/asimonutti33/SmartParking.git
cd SmartParking
2. Crear entorno virtual
bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
3. Instalar dependencias
bash
pip install -r requirements.txt
4. Configurar variables de entorno
bash
cp .env.example .env
Editar .env con tus credenciales:

env
# Django
SECRET_KEY=tu-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de datos
DB_NAME=smart_parking
DB_USER=postgres
DB_PASSWORD=tu-password
DB_HOST=localhost
DB_PORT=5432

# Email
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
REPORT_EMAIL=tu-email@ejemplo.com

# Telegram
SENSOR_TOKEN=Sensor_Token
TELEGRAM_BOT_TOKEN=tu-bot-token
TELEGRAM_ADMIN_CHAT_ID=tu-chat-id
5. Ejecutar migraciones
bash
python manage.py makemigrations
python manage.py migrate
6. Crear superusuario
bash
python manage.py createsuperuser
7. Cargar feriados (opcional)
bash
python manage.py cargar_feriados
8. Ejecutar servidor
bash
python manage.py runserver
Acceder a: http://127.0.0.1:8000/

🚀 Uso
Dashboard Principal
Acceder a http://tudominio.com:8000/ para ver:

Estado de espacios en tiempo real

Estadísticas generales

Botones de reserva (Programada / Espontánea)

Dashboard de Análisis
Acceder a http://tudominio.com:8000/analisis/ para ver:

Gráficos por horario

Gráficos por espacio

Forecasting de demanda

Panel de Administración
Acceder a http://tudominio.com:8000/admin/ para:

Gestionar espacios de estacionamiento

Ver reservas

Administrar feriados

Gestionar usuarios de Telegram

Script de la Raspberry Pi
En la Raspberry, ejecutar:

bash
python3 manage_serial.py
Esto iniciará:

Lectura del puerto serial (Arduino)

Heartbeat cada 30 segundos

Reconexión automática si el USB se desconecta

📁 Estructura del Proyecto
text
SmartParking/
│
├── config/                     # Configuración de Django
│   ├── settings.py             # Configuración general
│   ├── urls.py                 # URLs principales
│   └── wsgi.py                 # Punto de entrada WSGI
│
├── core/                       # Aplicación principal
│   ├── models.py               # Modelos (Espacio, Reserva, Feriado, etc.)
│   ├── services.py             # Lógica de negocio (ReservaService)
│   ├── views.py                # Vistas y API (SensorViewSet, etc.)
│   ├── serializers.py          # Serializers de DRF
│   ├── admin.py                # Panel de administración
│   ├── urls.py                 # URLs de la app
│   └── templates/              # Templates HTML
│       ├── dashboard.html      # Dashboard principal
│       └── analisis.html       # Dashboard de análisis
│
├── notifications/              # Sistema de notificaciones
│   ├── email_service.py        # Servicio de email (Gmail)
│   ├── telegram_service.py     # Servicio de Telegram
│   └── templates/emails/       # Templates de emails
│
├── reports/                    # Sistema de reportes
│   ├── report_service.py       # Generación de datos
│   └── pdf_generator.py        # Generación de PDFs
│
├── scripts/                    # Scripts auxiliares
│   ├── check_heartbeats.py     # Verificación de Raspberry
│   └── cargar_feriados.py      # Carga de feriados
│
├── manage_serial.py            # Script de la Raspberry (Serial → Cloud)
├── manage.py                   # Utilidad de Django
├── requirements.txt            # Dependencias
├── .env.example                # Ejemplo de variables de entorno
├── .gitignore                  # Archivos ignorados
└── README.md                   # Este archivo


🔌 API Endpoints
Sensores
Método	Endpoint	Descripción
POST	/api/sensor/estado/	Recibe datos del sensor/heartbeat

Ejemplo de petición:
bash
curl -X POST http://tudominio.com:8000/api/sensor/estado/ \
  -H "Content-Type: application/json" \
  -H "X-Sensor-Token: SmartParking2026SecureToken" \
  -d '{
    "type": "sensor_data",
    "id": 1,
    "estado": "LIBRE",
    "timestamp": "2026-08-28T10:00:00"
  }'

Espacios
Método	Endpoint	Descripción
GET	/api/espacios/	Lista todos los espacios

Reservas
Método	Endpoint	Descripción
GET	/api/reservas/	Lista todas las reservas
POST	/api/reservas/verificar/	Verifica disponibilidad
POST	/api/reservas/crear/	Crea una reserva
POST	/api/reservas/{id}/cancelar/	Cancela una reserva

Estadísticas
Método	Endpoint	Descripción
GET	/api/estadisticas/por_horario/	Distribución por hora
GET	/api/estadisticas/por_espacio/	Ocupación por espacio
GET	/api/estadisticas/forecasting/	Predicción de demanda
POST	/api/estadisticas/enviar_reporte/	Envía reporte por email

🧪 Pruebas
Casos de prueba documentados
ID	Caso de prueba	Estado
P-001	Solapamiento de reservas	✅ APROBADO
P-002	Reserva espontánea en espacio ocupado	✅ APROBADO
P-003	Reserva programada en espacio libre	✅ APROBADO
P-004	Reserva programada en domingo	✅ APROBADO
P-005	Reserva programada fuera de horario	✅ APROBADO
P-006	Reserva programada sábado tarde	✅ APROBADO
P-007	Desconexión de hardware (Arduino)	✅ APROBADO
P-008	Reserva espontánea con reserva futura	✅ APROBADO
P-009	Reserva en día feriado	✅ APROBADO


Ejecutar pruebas manuales
bash
# Probar endpoints con curl
curl http://tudominio.com:8000/api/espacios/

# Verificar heartbeats
python scripts/check_heartbeats.py

📄 Licencia
Este proyecto fue desarrollado con fines académicos como Proyecto Final de la carrera de Ingeniería en Computación en la Universidad Nacional de Rafaela (UNRaf).

Todos los derechos reservados al autor.

El código se comparte únicamente con fines educativos y de referencia. No se permite su uso comercial sin autorización expresa del autor.

👤 Autor
Alejandro Simonutti

🎓 Estudiante de Ingeniería en Computación - UNRaf

📧 Email: simonuttialejandro@gmail.com

🐙 GitHub: @asimonutti33



⭐ Si este proyecto te resultó útil, considerá darle una estrella ⭐

Desarrollado con 💙 en Rafaela, Argentina
