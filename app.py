from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import sys
import traceback
from urllib.parse import urlparse

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'tu_clave_secreta_aqui')

# Configuración de la base de datos
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///sistema.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_size': 5,
    'max_overflow': 10
}

logger.info(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
logger.info(f"Secret Key: {app.config['SECRET_KEY']}")

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelos
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=True)  # Hacemos el email opcional
    password = db.Column(db.String(120), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'docente' o 'tecnico'

    def __repr__(self):
        return f'<Usuario {self.nombre}>'

class Solicitud(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)  # 'notebook', 'cable_hdmi', 'cable_audio', 'asistencia'
    estado = db.Column(db.String(20), nullable=False, default='pendiente')  # pendiente, aprobada, denegada, en_proceso, prestado, devuelto
    fecha_solicitud = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    docente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tecnico_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    descripcion = db.Column(db.Text)
    fecha_resolucion = db.Column(db.DateTime)
    
    # Relaciones
    docente = db.relationship('Usuario', foreign_keys=[docente_id], backref='solicitudes_docente')
    tecnico = db.relationship('Usuario', foreign_keys=[tecnico_id], backref='solicitudes_tecnico')

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)  # 'notebook', 'cable_hdmi', 'cable_audio'
    numero_identificacion = db.Column(db.String(50), unique=True, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='disponible')  # disponible, prestado
    solicitud_actual = db.Column(db.Integer, db.ForeignKey('solicitud.id'))
    descripcion = db.Column(db.String(100))  # Para almacenar el nombre específico de la notebook

    def __repr__(self):
        return f'<Material {self.descripcion or self.numero_identificacion}>'

@login_manager.user_loader
def load_user(user_id):
    try:
        return Usuario.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
        return None

def crear_tecnicos_iniciales():
    try:
        tecnicos = [
            {'nombre': 'Juanjo', 'password': '123456'},
            {'nombre': 'Lucas', 'password': '123456'},
            {'nombre': 'Jorge', 'password': '123456'},
            {'nombre': 'Alexander', 'password': '123456'}
        ]
        
        for tecnico in tecnicos:
            usuario_existente = Usuario.query.filter_by(nombre=tecnico['nombre']).first()
            if not usuario_existente:
                logger.info(f"Creando técnico: {tecnico['nombre']}")
                nuevo_tecnico = Usuario(
                    nombre=tecnico['nombre'],
                    password=tecnico['password'],
                    tipo='tecnico'
                )
                db.session.add(nuevo_tecnico)
            else:
                logger.info(f"Técnico ya existe: {tecnico['nombre']}")
        
        db.session.commit()
        logger.info("Técnicos creados exitosamente")
        
        # Verificar técnicos creados
        tecnicos_db = Usuario.query.filter_by(tipo='tecnico').all()
        logger.info(f"Técnicos en la base de datos: {len(tecnicos_db)}")
        for tecnico in tecnicos_db:
            logger.info(f"Técnico: {tecnico.nombre}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al crear técnicos: {str(e)}")
        raise

def crear_materiales_iniciales():
    try:
        notebooks = [
            {'tipo': 'notebook', 'numero_identificacion': 'NB001', 'descripcion': 'Lenovo nueva1'},
            {'tipo': 'notebook', 'numero_identificacion': 'NB002', 'descripcion': 'Lenovo nueva2'},
            {'tipo': 'notebook', 'numero_identificacion': 'NB003', 'descripcion': 'Lenovo vieja'},
            {'tipo': 'notebook', 'numero_identificacion': 'NB004', 'descripcion': 'Bangho'},
            {'tipo': 'notebook', 'numero_identificacion': 'NB005', 'descripcion': 'Plateada'}
        ]
        
        for notebook in notebooks:
            material_existente = Material.query.filter_by(numero_identificacion=notebook['numero_identificacion']).first()
            if not material_existente:
                logger.info(f"Creando notebook: {notebook['descripcion']}")
                nuevo_material = Material(**notebook)
                db.session.add(nuevo_material)
            else:
                logger.info(f"Notebook ya existe: {notebook['descripcion']}")
        
        db.session.commit()
        logger.info("Notebooks creadas exitosamente")
        
        # Verificar notebooks creadas
        notebooks_db = Material.query.filter_by(tipo='notebook').all()
        logger.info(f"Notebooks en la base de datos: {len(notebooks_db)}")
        for notebook in notebooks_db:
            logger.info(f"Notebook: {notebook.descripcion} - Estado: {notebook.estado}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al crear notebooks: {str(e)}")
        raise

def test_db_connection():
    try:
        if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
            # Para SQLite, solo verificamos que el directorio existe
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            if db_path:
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            logger.info("Conexión a SQLite verificada")
            return True
            
        # Para PostgreSQL
        import psycopg2
        from psycopg2 import OperationalError
        
        parsed = urlparse(app.config['SQLALCHEMY_DATABASE_URI'])
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port
        )
        conn.close()
        logger.info("Conexión a PostgreSQL exitosa")
        return True
    except Exception as e:
        logger.error(f"Error de conexión a la base de datos: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def init_db():
    try:
        if not test_db_connection():
            raise Exception("No se pudo conectar a la base de datos")
            
        logger.info("Iniciando creación de tablas...")
        db.create_all()
        logger.info("Tablas creadas exitosamente")
        
        logger.info("Iniciando creación de técnicos...")
        crear_tecnicos_iniciales()
        logger.info("Técnicos creados exitosamente")
        
        logger.info("Iniciando creación de notebooks...")
        crear_materiales_iniciales()
        logger.info("Notebooks creadas exitosamente")
        
        logger.info("Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"Error al inicializar la base de datos: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Error interno del servidor: {str(error)}")
    logger.error(traceback.format_exc())
    return "Error interno del servidor", 500

# Rutas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if password != confirm_password:
                flash('Las contraseñas no coinciden')
                return redirect(url_for('registro'))
            
            if Usuario.query.filter_by(nombre=nombre).first():
                flash('El nombre de usuario ya está registrado')
                return redirect(url_for('registro'))
            
            nuevo_docente = Usuario(
                nombre=nombre,
                password=password,  # En producción, usar hash de contraseña
                tipo='docente'
            )
            
            db.session.add(nuevo_docente)
            db.session.commit()
            flash('Registro exitoso. Por favor, inicia sesión.')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error en registro: {str(e)}")
            flash('Error al registrar usuario')
            return redirect(url_for('registro'))
    
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre')
            password = request.form.get('password')
            logger.info(f"Intento de login para usuario: {nombre}")
            
            user = Usuario.query.filter_by(nombre=nombre).first()
            if user:
                logger.info(f"Usuario encontrado: {user.nombre}, tipo: {user.tipo}")
                if user.password == password:  # En producción, usar hash de contraseña
                    login_user(user)
                    logger.info(f"Login exitoso para: {user.nombre}")
                    return redirect(url_for('dashboard'))
                else:
                    logger.warning(f"Contraseña incorrecta para: {nombre}")
            else:
                logger.warning(f"Usuario no encontrado: {nombre}")
            
            flash('Credenciales inválidas')
        except Exception as e:
            logger.error(f"Error en login: {str(e)}")
            logger.error(traceback.format_exc())
            flash('Error al iniciar sesión')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        if current_user.tipo == 'docente':
            solicitudes = Solicitud.query.filter_by(docente_id=current_user.id).all()
        else:
            solicitudes = Solicitud.query.all()
        return render_template('dashboard.html', solicitudes=solicitudes)
    except Exception as e:
        logger.error(f"Error en dashboard: {str(e)}")
        flash('Error al cargar el dashboard')
        return redirect(url_for('index'))

@app.route('/solicitud/nueva', methods=['GET', 'POST'])
@login_required
def nueva_solicitud():
    if current_user.tipo not in ['docente', 'tecnico']:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            tipo = request.form.get('tipo')
            descripcion = request.form.get('descripcion')
            docente_id = request.form.get('docente_id')
            notebook_id = request.form.get('notebook')
            
            logger.info(f"Tipo de solicitud recibido: {tipo}")
            logger.info(f"Descripción: {descripcion}")
            logger.info(f"ID del docente: {docente_id}")
            logger.info(f"ID de la notebook: {notebook_id}")
            
            if current_user.tipo == 'tecnico' and not docente_id:
                flash('Debe seleccionar un docente')
                return redirect(url_for('nueva_solicitud'))
            
            if tipo == 'notebook' and not notebook_id:
                flash('Debe seleccionar una notebook')
                return redirect(url_for('nueva_solicitud'))
            
            nueva_solicitud = Solicitud(
                tipo=tipo,
                descripcion=descripcion,
                docente_id=docente_id if current_user.tipo == 'tecnico' else current_user.id
            )
            db.session.add(nueva_solicitud)
            db.session.flush()  # Para obtener el ID de la solicitud
            
            if tipo == 'notebook' and notebook_id:
                notebook = Material.query.get(notebook_id)
                if notebook and notebook.estado == 'disponible':
                    notebook.estado = 'prestado'
                    notebook.solicitud_actual = nueva_solicitud.id
                    db.session.add(notebook)
            
            db.session.commit()
            flash('Solicitud creada exitosamente')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al crear solicitud: {str(e)}")
            flash('Error al crear la solicitud')
            return redirect(url_for('nueva_solicitud'))
    
    try:
        docentes = Usuario.query.filter_by(tipo='docente').all() if current_user.tipo == 'tecnico' else None
        # Obtener notebooks disponibles
        notebooks_disponibles = Material.query.filter_by(tipo='notebook', estado='disponible').all()
        logger.info(f"Notebooks disponibles: {len(notebooks_disponibles)}")
        for notebook in notebooks_disponibles:
            logger.info(f"Notebook disponible: {notebook.descripcion}")
        return render_template('nueva_solicitud.html', docentes=docentes, notebooks=notebooks_disponibles)
    except Exception as e:
        logger.error(f"Error al cargar formulario de nueva solicitud: {str(e)}")
        flash('Error al cargar el formulario')
        return redirect(url_for('dashboard'))

@app.route('/solicitud/<int:id>/aprobar', methods=['POST'])
@login_required
def aprobar_solicitud(id):
    if current_user.tipo != 'tecnico':
        return redirect(url_for('dashboard'))
    
    try:
        solicitud = Solicitud.query.get_or_404(id)
        solicitud.estado = 'aprobada'
        solicitud.tecnico_id = current_user.id
        
        if solicitud.tipo in ['notebook', 'cable_hdmi', 'cable_audio']:
            solicitud.estado = 'prestado'
        
        db.session.commit()
        flash('Solicitud aprobada exitosamente')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al aprobar solicitud: {str(e)}")
        flash('Error al aprobar la solicitud')
    return redirect(url_for('dashboard'))

@app.route('/solicitud/<int:id>/denegar', methods=['POST'])
@login_required
def denegar_solicitud(id):
    if current_user.tipo != 'tecnico':
        return redirect(url_for('dashboard'))
    
    try:
        solicitud = Solicitud.query.get_or_404(id)
        solicitud.estado = 'denegada'
        solicitud.tecnico_id = current_user.id
        db.session.commit()
        flash('Solicitud denegada')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al denegar solicitud: {str(e)}")
        flash('Error al denegar la solicitud')
    return redirect(url_for('dashboard'))

@app.route('/solicitud/<int:id>/devolver', methods=['POST'])
@login_required
def devolver_solicitud(id):
    if current_user.tipo != 'tecnico':
        return redirect(url_for('dashboard'))
    
    try:
        solicitud = Solicitud.query.get_or_404(id)
        if solicitud.estado == 'prestado':
            solicitud.estado = 'devuelto'
            solicitud.fecha_resolucion = datetime.utcnow()
            
            # Si es una notebook, actualizar su estado
            if solicitud.tipo == 'notebook':
                notebook = Material.query.filter_by(solicitud_actual=solicitud.id).first()
                if notebook:
                    notebook.estado = 'disponible'
                    notebook.solicitud_actual = None
            
            db.session.commit()
            flash('Material marcado como devuelto')
        else:
            flash('Esta solicitud no puede ser marcada como devuelta')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al marcar como devuelto: {str(e)}")
        flash('Error al marcar como devuelto')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False) 