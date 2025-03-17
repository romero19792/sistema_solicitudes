# Sistema de Solicitudes para Docentes y Técnicos

Este sistema permite a los docentes realizar solicitudes de materiales y asistencia técnica, mientras que los técnicos pueden gestionar estas solicitudes.

## Características

- Gestión de solicitudes de materiales (computadoras, cables HDMI, cables de audio)
- Solicitudes de asistencia técnica
- Sistema de notificaciones para técnicos
- Seguimiento del estado de las solicitudes
- Control de inventario de materiales
- Interfaz intuitiva y fácil de usar

## Requisitos

- Python 3.8 o superior
- Flask y sus dependencias (listadas en requirements.txt)

## Instalación

1. Clonar el repositorio:
```bash
git clone [URL_DEL_REPOSITORIO]
cd sistema_solicitudes
```

2. Crear un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
Crear un archivo `.env` con las siguientes variables:
```
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=tu_clave_secreta_aqui
```

5. Inicializar la base de datos:
```bash
flask db init
flask db migrate
flask db upgrade
```

## Uso

1. Iniciar el servidor:
```bash
flask run
```

2. Acceder a la aplicación:
Abrir el navegador y visitar `http://localhost:5000`

## Estructura del Proyecto

```
sistema_solicitudes/
├── app.py              # Aplicación principal
├── requirements.txt    # Dependencias del proyecto
├── templates/         # Plantillas HTML
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   └── nueva_solicitud.html
└── README.md          # Este archivo
```

## Roles de Usuario

### Docentes
- Pueden crear nuevas solicitudes
- Ver el estado de sus solicitudes
- Recibir notificaciones sobre actualizaciones

### Técnicos
- Recibir notificaciones de nuevas solicitudes
- Aprobar o denegar solicitudes
- Actualizar el estado de las solicitudes
- Gestionar el inventario de materiales

## Contribuir

1. Fork el repositorio
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles. 