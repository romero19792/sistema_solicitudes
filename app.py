from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'tu_clave_secreta_aqui')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///sistema.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Asegurarse de que la URL de la base de datos comience con postgresql://
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

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
    return Usuario.query.get(int(user_id))

def crear_tecnicos_iniciales():
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
    
    try:
        db.session.commit()
        print("Técnicos creados exitosamente")
    except Exception as e:
        db.session.rollback()
        print(f"Error al crear técnicos: {str(e)}")

# Rutas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
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
        
        try:
            db.session.add(nuevo_docente)
            db.session.commit()
            flash('Registro exitoso. Por favor, inicia sesión.')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Error al registrar usuario')
            return redirect(url_for('registro'))
    
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = Usuario.query.filter_by(email=email).first()
        
        if user and user.password == password:  # En producción, usar hash de contraseña
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Credenciales inválidas')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.tipo == 'docente':
        solicitudes = Solicitud.query.filter_by(docente_id=current_user.id).all()
    else:
        solicitudes = Solicitud.query.all()
    return render_template('dashboard.html', solicitudes=solicitudes)

@app.route('/solicitud/nueva', methods=['GET', 'POST'])
@login_required
def nueva_solicitud():
    if current_user.tipo not in ['docente', 'tecnico']:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
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
    
    # Obtener lista de docentes para el formulario
    docentes = Usuario.query.filter_by(tipo='docente').all() if current_user.tipo == 'tecnico' else None
    return render_template('nueva_solicitud.html', docentes=docentes)

@app.route('/solicitud/<int:id>/aprobar', methods=['POST'])
@login_required
def aprobar_solicitud(id):
    if current_user.tipo != 'tecnico':
        return redirect(url_for('dashboard'))
    
    solicitud = Solicitud.query.get_or_404(id)
    solicitud.estado = 'aprobada'
    solicitud.tecnico_id = current_user.id
    
    if solicitud.tipo in ['computadora', 'cable_hdmi', 'cable_audio']:
        solicitud.estado = 'prestado'
    
    db.session.commit()
    flash('Solicitud aprobada exitosamente')
    return redirect(url_for('dashboard'))

@app.route('/solicitud/<int:id>/denegar', methods=['POST'])
@login_required
def denegar_solicitud(id):
    if current_user.tipo != 'tecnico':
        return redirect(url_for('dashboard'))
    
    solicitud = Solicitud.query.get_or_404(id)
    solicitud.estado = 'denegada'
    solicitud.tecnico_id = current_user.id
    db.session.commit()
    flash('Solicitud denegada')
    return redirect(url_for('dashboard'))

@app.route('/solicitud/<int:id>/devolver', methods=['POST'])
@login_required
def devolver_solicitud(id):
    if current_user.tipo != 'tecnico':
        return redirect(url_for('dashboard'))
    
    solicitud = Solicitud.query.get_or_404(id)
    if solicitud.estado == 'prestado':
        solicitud.estado = 'devuelto'
        solicitud.fecha_resolucion = datetime.utcnow()
        db.session.commit()
        flash('Material marcado como devuelto')
    else:
        flash('Esta solicitud no puede ser marcada como devuelta')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        crear_tecnicos_iniciales()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False) 