from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
from dotenv import load_dotenv
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'tu_clave_secreta_aqui')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///sistema.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Asegurarse de que la URL de la base de datos comience con postgresql://
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

logger.info(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelos
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'docente' o 'tecnico'

class Solicitud(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)  # 'computadora', 'cable_hdmi', 'cable_audio', 'asistencia'
    estado = db.Column(db.String(20), nullable=False, default='pendiente')  # pendiente, aprobada, denegada, en_proceso, prestado, devuelto
    fecha_solicitud = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    docente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tecnico_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    descripcion = db.Column(db.Text)
    fecha_resolucion = db.Column(db.DateTime)

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)  # 'computadora', 'cable_hdmi', 'cable_audio'
    numero_identificacion = db.Column(db.String(50), unique=True, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='disponible')  # disponible, prestado
    solicitud_actual = db.Column(db.Integer, db.ForeignKey('solicitud.id'))

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
            {'nombre': 'Juanjo', 'email': 'juanjo@institucion.edu', 'password': 'juanjo123'},
            {'nombre': 'Lucas', 'email': 'lucas@institucion.edu', 'password': 'lucas123'},
            {'nombre': 'Jorge', 'email': 'jorge@institucion.edu', 'password': 'jorge123'},
            {'nombre': 'Alexander', 'email': 'alexander@institucion.edu', 'password': 'alexander123'}
        ]
        
        for tecnico in tecnicos:
            if not Usuario.query.filter_by(email=tecnico['email']).first():
                nuevo_tecnico = Usuario(
                    nombre=tecnico['nombre'],
                    email=tecnico['email'],
                    password=tecnico['password'],  # En producción, usar hash de contraseña
                    tipo='tecnico'
                )
                db.session.add(nuevo_tecnico)
        
        db.session.commit()
        logger.info("Técnicos creados exitosamente")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al crear técnicos: {str(e)}")

# Rutas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if password != confirm_password:
                flash('Las contraseñas no coinciden')
                return redirect(url_for('registro'))
            
            if Usuario.query.filter_by(email=email).first():
                flash('El correo electrónico ya está registrado')
                return redirect(url_for('registro'))
            
            nuevo_docente = Usuario(
                nombre=nombre,
                email=email,
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
            email = request.form.get('email')
            password = request.form.get('password')
            user = Usuario.query.filter_by(email=email).first()
            
            if user and user.password == password:  # En producción, usar hash de contraseña
                login_user(user)
                return redirect(url_for('dashboard'))
            flash('Credenciales inválidas')
        except Exception as e:
            logger.error(f"Error en login: {str(e)}")
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
            
            if current_user.tipo == 'tecnico' and not docente_id:
                flash('Debe seleccionar un docente')
                return redirect(url_for('nueva_solicitud'))
            
            nueva_solicitud = Solicitud(
                tipo=tipo,
                descripcion=descripcion,
                docente_id=docente_id if current_user.tipo == 'tecnico' else current_user.id
            )
            db.session.add(nueva_solicitud)
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
        return render_template('nueva_solicitud.html', docentes=docentes)
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
        
        if solicitud.tipo in ['computadora', 'cable_hdmi', 'cable_audio']:
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
        try:
            db.create_all()
            crear_tecnicos_iniciales()
            logger.info("Base de datos inicializada correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar la base de datos: {str(e)}")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False) 