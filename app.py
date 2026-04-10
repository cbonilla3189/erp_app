import os
import secrets
import datetime
import re
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash
)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

load_dotenv()

# -----------------------------
# Configuración
# -----------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
mail = Mail(app)


# -----------------------------
# Modelos
# -----------------------------
class Usuario(db.Model):
    __tablename__ = "usuarios"
    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(100), nullable=False)
    apellido    = db.Column(db.String(100), nullable=False)
    empresa     = db.Column(db.String(200))
    correo      = db.Column(db.String(200), unique=True, nullable=False)
    ruc         = db.Column(db.String(50))
    dv          = db.Column(db.String(10))
    telefono    = db.Column(db.String(30))
    username    = db.Column(db.String(80), unique=True, nullable=False)
    password    = db.Column(db.String(256), nullable=False)
    verificado    = db.Column(db.Integer, default=0)
    rol           = db.Column(db.String(20), default='viewer')
    empresa_admin    = db.Column(db.Boolean, default=False)
    session_timeout  = db.Column(db.Integer, default=120)
    productos   = db.relationship("Producto", backref="usuario", lazy=True)
    tokens      = db.relationship("TokenVerificacion", backref="usuario", lazy=True)


class TokenVerificacion(db.Model):
    __tablename__ = "tokens_verificacion"
    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    token             = db.Column(db.String(100), unique=True, nullable=False)
    fecha_expiracion  = db.Column(db.DateTime, nullable=False)


class Producto(db.Model):
    __tablename__ = "productos"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    nombre      = db.Column(db.String(200), nullable=False)
    categoria   = db.Column(db.String(100))
    cantidad    = db.Column(db.Integer, default=0)
    precio      = db.Column(db.Float, default=0)
    creado_en   = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    stock_minimo  = db.Column(db.Integer, default=5)
    codigo_barras = db.Column(db.String(100))
    inventario_id = db.Column(db.Integer, db.ForeignKey("inventarios.id"))
    categoria_id  = db.Column(db.Integer, db.ForeignKey("categorias.id"))




class Inventario(db.Model):
    __tablename__ = "inventarios"
    id          = db.Column(db.Integer, primary_key=True)
    empresa     = db.Column(db.String(200), nullable=False)
    nombre      = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    color       = db.Column(db.String(7), default="#561d9c")
    creado_por  = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    creado_en   = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    productos   = db.relationship("Producto", backref="inventario", lazy=True)


class Categoria(db.Model):
    __tablename__ = "categorias"
    id            = db.Column(db.Integer, primary_key=True)
    inventario_id = db.Column(db.Integer, db.ForeignKey("inventarios.id"), nullable=False)
    nombre        = db.Column(db.String(100), nullable=False)
    descripcion   = db.Column(db.Text)
    tipo          = db.Column(db.String(20), default="stock")
    stock_minimo  = db.Column(db.Integer, default=5)
    color         = db.Column(db.String(7), default="#561d9c")
    creado_en     = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    productos     = db.relationship("Producto", backref="categoria_obj", lazy=True)




class Plan(db.Model):
    __tablename__ = "planes"
    id          = db.Column(db.Integer, primary_key=True)
    empresa     = db.Column(db.String(200), nullable=False)
    nombre      = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    costo       = db.Column(db.Numeric(12,2), nullable=False)
    frecuencia  = db.Column(db.String(20), default="mensual")
    color       = db.Column(db.String(7), default="#561d9c")
    activo      = db.Column(db.Boolean, default=True)
    creado_en   = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    incluye     = db.relationship("PlanIncluye", backref="plan", lazy=True, cascade="all, delete-orphan")
    horarios    = db.relationship("PlanHorario", backref="plan", lazy=True, cascade="all, delete-orphan")


class PlanIncluye(db.Model):
    __tablename__ = "plan_incluye"
    id          = db.Column(db.Integer, primary_key=True)
    plan_id     = db.Column(db.Integer, db.ForeignKey("planes.id"))
    descripcion = db.Column(db.String(200), nullable=False)


class PlanHorario(db.Model):
    __tablename__ = "plan_horarios"
    id          = db.Column(db.Integer, primary_key=True)
    plan_id     = db.Column(db.Integer, db.ForeignKey("planes.id"))
    dia         = db.Column(db.String(20), nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin    = db.Column(db.Time, nullable=False)
    actividad   = db.Column(db.String(100), nullable=False)
    instructor  = db.Column(db.String(100))

class Cliente(db.Model):
    __tablename__ = "clientes"
    id         = db.Column(db.Integer, primary_key=True)
    empresa    = db.Column(db.String(200))
    nombre     = db.Column(db.String(100), nullable=False)
    apellido   = db.Column(db.String(100))
    ruc        = db.Column(db.String(50))
    dv         = db.Column(db.String(10))
    correo     = db.Column(db.String(150))
    telefono   = db.Column(db.String(30))
    direccion  = db.Column(db.Text)
    creado_en  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    ventas     = db.relationship("Venta", backref="cliente_rel", lazy=True)
    suscripciones = db.relationship("Suscripcion", backref="cliente_rel", lazy=True)
    servicios  = db.relationship("ServicioFijo", backref="cliente_rel", lazy=True)


class Venta(db.Model):
    __tablename__ = "ventas"
    id              = db.Column(db.Integer, primary_key=True)
    empresa         = db.Column(db.String(200))
    tipo            = db.Column(db.String(20), nullable=False)
    numero_factura  = db.Column(db.String(50))
    cliente_id      = db.Column(db.Integer, db.ForeignKey("clientes.id"))
    cliente_nombre  = db.Column(db.String(200))
    cliente_ruc     = db.Column(db.String(50))
    cliente_correo  = db.Column(db.String(150))
    subtotal        = db.Column(db.Numeric(12,2), default=0)
    itbms           = db.Column(db.Numeric(12,2), default=0)
    descuento       = db.Column(db.Numeric(12,2), default=0)
    total           = db.Column(db.Numeric(12,2), default=0)
    metodo_pago     = db.Column(db.String(30))
    documento       = db.Column(db.String(20), default="recibo")
    estado          = db.Column(db.String(20), default="pagado")
    notas           = db.Column(db.Text)
    creado_por      = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    creado_en       = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    items           = db.relationship("VentaItem", backref="venta", lazy=True, cascade="all, delete-orphan")


class VentaItem(db.Model):
    __tablename__ = "venta_items"
    id              = db.Column(db.Integer, primary_key=True)
    venta_id        = db.Column(db.Integer, db.ForeignKey("ventas.id"))
    producto_id     = db.Column(db.Integer, db.ForeignKey("productos.id"))
    descripcion     = db.Column(db.String(200))
    cantidad        = db.Column(db.Numeric(10,2), default=1)
    precio_unitario = db.Column(db.Numeric(12,2), default=0)
    total           = db.Column(db.Numeric(12,2), default=0)


class Suscripcion(db.Model):
    __tablename__ = "suscripciones"
    id             = db.Column(db.Integer, primary_key=True)
    empresa        = db.Column(db.String(200))
    cliente_id     = db.Column(db.Integer, db.ForeignKey("clientes.id"))
    cliente_nombre = db.Column(db.String(200))
    plan           = db.Column(db.String(100))
    descripcion    = db.Column(db.Text)
    monto          = db.Column(db.Numeric(12,2))
    frecuencia     = db.Column(db.String(20), default="mensual")
    fecha_inicio   = db.Column(db.Date)
    proximo_cobro  = db.Column(db.Date)
    estado         = db.Column(db.String(20), default="activa")
    metodo_pago    = db.Column(db.String(30))
    plan_id        = db.Column(db.Integer, db.ForeignKey("planes.id"))
    creado_por     = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    creado_en      = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class ServicioFijo(db.Model):
    __tablename__ = "servicios_fijos"
    id             = db.Column(db.Integer, primary_key=True)
    empresa        = db.Column(db.String(200))
    cliente_id     = db.Column(db.Integer, db.ForeignKey("clientes.id"))
    cliente_nombre = db.Column(db.String(200))
    descripcion    = db.Column(db.String(200))
    monto          = db.Column(db.Numeric(12,2))
    periodo        = db.Column(db.String(20))
    fecha_inicio   = db.Column(db.Date)
    fecha_fin      = db.Column(db.Date)
    estado         = db.Column(db.String(20), default="activo")
    metodo_pago    = db.Column(db.String(30))
    creado_por     = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    creado_en      = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class CrmContacto(db.Model):
    __tablename__ = "crm_contactos"
    id               = db.Column(db.Integer, primary_key=True)
    empresa_id       = db.Column(db.String(200))
    nombre           = db.Column(db.String(100), nullable=False)
    apellido         = db.Column(db.String(100))
    empresa_contacto = db.Column(db.String(200))
    cargo            = db.Column(db.String(100))
    correo           = db.Column(db.String(150))
    telefono         = db.Column(db.String(30))
    origen           = db.Column(db.String(50))
    estado           = db.Column(db.String(20), default="activo")
    notas            = db.Column(db.Text)
    creado_por       = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    creado_en        = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    oportunidades    = db.relationship("CrmOportunidad", backref="contacto", lazy=True)
    interacciones    = db.relationship("CrmInteraccion", backref="contacto", lazy=True, cascade="all, delete-orphan")
    tareas           = db.relationship("CrmTarea", backref="contacto", lazy=True)


class CrmOportunidad(db.Model):
    __tablename__ = "crm_oportunidades"
    id             = db.Column(db.Integer, primary_key=True)
    empresa_id     = db.Column(db.String(200))
    contacto_id    = db.Column(db.Integer, db.ForeignKey("crm_contactos.id"))
    titulo         = db.Column(db.String(200), nullable=False)
    valor          = db.Column(db.Numeric(12,2), default=0)
    etapa          = db.Column(db.String(30), default="prospecto")
    responsable_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    fecha_cierre   = db.Column(db.Date)
    probabilidad   = db.Column(db.Integer, default=0)
    notas          = db.Column(db.Text)
    flujo_id       = db.Column(db.Integer, db.ForeignKey("flujos.id"))
    etapa_flujo_id = db.Column(db.Integer, db.ForeignKey("flujo_etapas.id"))
    creado_en      = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    interacciones  = db.relationship("CrmInteraccion", backref="oportunidad", lazy=True)
    tareas         = db.relationship("CrmTarea", backref="oportunidad", lazy=True)


class CrmInteraccion(db.Model):
    __tablename__ = "crm_interacciones"
    id              = db.Column(db.Integer, primary_key=True)
    contacto_id     = db.Column(db.Integer, db.ForeignKey("crm_contactos.id"))
    oportunidad_id  = db.Column(db.Integer, db.ForeignKey("crm_oportunidades.id"))
    tipo            = db.Column(db.String(30), nullable=False)
    descripcion     = db.Column(db.Text)
    resultado       = db.Column(db.Text)
    fecha           = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    creado_por      = db.Column(db.Integer, db.ForeignKey("usuarios.id"))


class CrmTarea(db.Model):
    __tablename__ = "crm_tareas"
    id              = db.Column(db.Integer, primary_key=True)
    empresa_id      = db.Column(db.String(200))
    contacto_id     = db.Column(db.Integer, db.ForeignKey("crm_contactos.id"))
    oportunidad_id  = db.Column(db.Integer, db.ForeignKey("crm_oportunidades.id"))
    descripcion     = db.Column(db.String(300), nullable=False)
    asignado_a      = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    fecha_limite    = db.Column(db.Date)
    estado          = db.Column(db.String(20), default="pendiente")
    prioridad       = db.Column(db.String(20), default="media")
    creado_por      = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    creado_en       = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class Flujo(db.Model):
    __tablename__ = "flujos"
    id          = db.Column(db.Integer, primary_key=True)
    empresa     = db.Column(db.String(200), nullable=False)
    nombre      = db.Column(db.String(100), nullable=False)
    modulo      = db.Column(db.String(30), nullable=False)
    descripcion = db.Column(db.Text)
    activo      = db.Column(db.Boolean, default=True)
    creado_en   = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    etapas      = db.relationship("FlujoEtapa", backref="flujo", lazy=True,
                    order_by="FlujoEtapa.orden", cascade="all, delete-orphan")
    reglas      = db.relationship("FlujoRegla", backref="flujo", lazy=True,
                    cascade="all, delete-orphan")


class FlujoEtapa(db.Model):
    __tablename__ = "flujo_etapas"
    id             = db.Column(db.Integer, primary_key=True)
    flujo_id       = db.Column(db.Integer, db.ForeignKey("flujos.id"))
    nombre         = db.Column(db.String(100), nullable=False)
    color          = db.Column(db.String(7), default="#561d9c")
    orden          = db.Column(db.Integer, default=0)
    responsable_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    es_final       = db.Column(db.Boolean, default=False)
    es_perdido     = db.Column(db.Boolean, default=False)
    reglas         = db.relationship("FlujoRegla", backref="etapa", lazy=True,
                        cascade="all, delete-orphan")


class FlujoRegla(db.Model):
    __tablename__ = "flujo_reglas"
    id            = db.Column(db.Integer, primary_key=True)
    flujo_id      = db.Column(db.Integer, db.ForeignKey("flujos.id"))
    etapa_id      = db.Column(db.Integer, db.ForeignKey("flujo_etapas.id"))
    trigger       = db.Column(db.String(50), nullable=False)
    accion        = db.Column(db.String(50), nullable=False)
    destinatario  = db.Column(db.String(30), default="responsable")
    mensaje       = db.Column(db.Text)
    activo        = db.Column(db.Boolean, default=True)


class CampoPersonalizado(db.Model):
    __tablename__ = "campos_personalizados"
    id         = db.Column(db.Integer, primary_key=True)
    empresa    = db.Column(db.String(200), nullable=False)
    nombre     = db.Column(db.String(100), nullable=False)
    tipo       = db.Column(db.String(20), nullable=False)
    opciones   = db.Column(db.Text)
    creado_en     = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    inventario_id = db.Column(db.Integer, db.ForeignKey("inventarios.id"))
    categoria_id  = db.Column(db.Integer, db.ForeignKey("categorias.id"))
    valores    = db.relationship("ValorCampo", backref="campo", lazy=True, cascade="all, delete-orphan")


class ValorCampo(db.Model):
    __tablename__ = "valores_campos"
    id          = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    campo_id    = db.Column(db.Integer, db.ForeignKey("campos_personalizados.id"), nullable=False)
    valor       = db.Column(db.Text)
    __table_args__ = (db.UniqueConstraint("producto_id", "campo_id"),)

# -----------------------------
# Init DB
# -----------------------------
def init_db():
    db.create_all()
    if not Usuario.query.filter_by(username="carlos").first():
        admin = Usuario(
            nombre="Admin", apellido="Principal", empresa="MiEmpresa",
            correo="admin@example.com", username="carlos",
            password=generate_password_hash("1234"), verificado=1
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Usuario admin creado: carlos / 1234")


# -----------------------------
# Context processor
# -----------------------------
@app.before_request
def check_session_timeout():
    if "user_id" in session:
        try:
            now = datetime.datetime.utcnow()
            last_active = session.get("last_active")
            if last_active:
                last_active_dt = datetime.datetime.fromisoformat(last_active)
                user = Usuario.query.get(session["user_id"])
                timeout_minutes = (user.session_timeout or 120) if user else 120
                if (now - last_active_dt).total_seconds() > timeout_minutes * 60:
                    session.clear()
                    return redirect(url_for("login"))
            session["last_active"] = now.isoformat()
        except Exception:
            session["last_active"] = datetime.datetime.utcnow().isoformat()


@app.context_processor
def inject_user():
    username = session.get("username") or ""
    if not isinstance(username, str):
        username = str(username)
    return {"usuario": username}


# -----------------------------
# Validación contraseña
# -----------------------------
def password_valid(password: str) -> tuple[bool, str]:
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_\-+=]).{8,}$'
    if not re.match(pattern, password):
        return False, ("La contraseña debe tener: mínimo 8 caracteres, "
                       "al menos 1 mayúscula, 1 minúscula, 1 número y "
                       "1 carácter especial (!@#$%^&*()_-+=).")
    return True, ""


# -----------------------------
# Rutas públicas
# -----------------------------
@app.route("/")
def home():
    if "user_id" in session:
        user = Usuario.query.get(session["user_id"])
        if user and user.username == "carlos":
            return redirect(url_for("admin_panel"))
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username_or_email = request.form.get("username")
        password = request.form.get("password")
        user = Usuario.query.filter(
            (Usuario.username == username_or_email) |
            (Usuario.correo == username_or_email)
        ).first()
        if user and check_password_hash(user.password, password):
            if user.verificado == 0:
                return render_template("verify.html", mensaje="Tu cuenta no está verificada.")
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Inicio de sesión correcto", "success")
            return redirect(url_for("home"))
        flash("Usuario o contraseña incorrectos", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre    = request.form.get("nombre", "").strip().title()
        apellido  = request.form.get("apellido", "").strip().title()
        empresa   = request.form.get("empresa", "").strip().title()
        correo    = request.form.get("correo", "").strip().lower()
        ruc       = request.form.get("ruc", "").strip()
        dv        = request.form.get("dv", "").strip()
        telefono  = request.form.get("telefono", "").strip()
        username  = request.form.get("username", "").strip()
        password  = request.form.get("password", "")
        confirm   = request.form.get("confirm_password", "")

        if not all([nombre, apellido, correo, username, password]):
            flash("Por favor completa los campos obligatorios.", "warning")
            return render_template("register.html")
        if password != confirm:
            flash("Las contraseñas no coinciden.", "warning")
            return render_template("register.html")
        ok, msg = password_valid(password)
        if not ok:
            flash(msg, "warning")
            return render_template("register.html")

        if Usuario.query.filter_by(correo=correo).first() or \
           Usuario.query.filter_by(username=username).first():
            flash("Usuario o correo ya registrado.", "danger")
            return render_template("register.html")

        empresa_existe = Usuario.query.filter_by(empresa=empresa).filter(
            Usuario.empresa != None, Usuario.empresa != "").first() if empresa else None
        es_admin_empresa = not empresa_existe
        user = Usuario(
            nombre=nombre, apellido=apellido, empresa=empresa,
            correo=correo, ruc=ruc, dv=dv, telefono=telefono,
            username=username, password=generate_password_hash(password),
            rol="admin" if es_admin_empresa else "viewer",
            empresa_admin=es_admin_empresa
        )
        db.session.add(user)
        db.session.commit()

        import random
        codigo = str(random.randint(100000, 999999))
        expiracion = datetime.datetime.now() + datetime.timedelta(minutes=30)
        tv = TokenVerificacion(user_id=user.id, token=codigo, fecha_expiracion=expiracion)
        db.session.add(tv)
        db.session.commit()

        try:
            msg = Message("Verifica tu cuenta — aruna",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[correo])
            msg.body = (f"Hola {nombre},\n\n"
                        f"Tu código de verificación es:\n\n"
                        f"  {codigo}\n\n"
                        f"Ingresa este código en la página de verificación.\n"
                        f"Expira en 30 minutos.\n\n"
                        f"— Equipo aruna")
            mail.send(msg)
        except Exception as e:
            print("Error enviando correo:", e)

        return redirect(url_for("verify_code", user_id=user.id))
    return render_template("register.html")


@app.route("/verify/<token>")
def verify(token):
    tv = TokenVerificacion.query.filter_by(token=token).first()
    if not tv:
        return render_template("verify.html", mensaje="Token inválido o ya usado.")
    if datetime.datetime.now() > tv.fecha_expiracion:
        db.session.delete(tv)
        db.session.commit()
        return render_template("verify.html", mensaje="El enlace ha expirado.")
    user = Usuario.query.get(tv.user_id)
    user.verificado = 1
    db.session.delete(tv)
    db.session.commit()
    return render_template("verify.html", mensaje="Cuenta verificada. Ya puedes iniciar sesión.")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("home"))


# -----------------------------
# Admin
# -----------------------------
@app.route("/admin")
def admin_panel():
    if "user_id" not in session or session.get("username") != "carlos":
        flash("Acceso restringido.", "warning")
        return redirect(url_for("login"))
    empresas = db.session.query(Usuario.empresa).filter(
        Usuario.empresa != "").distinct().all()
    usuarios = Usuario.query.all()
    return render_template("admin.html", empresas=empresas, usuarios=usuarios)


@app.route("/admin/eliminar/<int:id>", methods=["POST", "GET"])
def eliminar_usuario(id):
    if "user_id" not in session or session.get("username") != "carlos":
        return redirect(url_for("login"))
    user = Usuario.query.get(id)
    if user and user.username == "carlos":
        flash("No puedes eliminar al administrador.", "warning")
        return redirect(url_for("admin_panel"))
    db.session.delete(user)
    db.session.commit()
    flash("Usuario eliminado.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/editar/<int:id>", methods=["GET", "POST"])
def editar_usuario(id):
    if "user_id" not in session or session.get("username") != "carlos":
        return redirect(url_for("login"))
    user = Usuario.query.get(id)
    if not user:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("admin_panel"))
    if request.method == "POST":
        user.nombre   = request.form.get("nombre", user.nombre).strip().title()
        user.apellido = request.form.get("apellido", user.apellido).strip().title()
        user.empresa  = request.form.get("empresa", user.empresa).strip().title()
        user.correo   = request.form.get("correo", user.correo).strip()
        user.telefono = request.form.get("telefono", user.telefono).strip()
        user.ruc      = request.form.get("ruc", user.ruc).strip()
        user.dv       = request.form.get("dv", user.dv).strip()
        db.session.commit()
        flash("Usuario actualizado.", "success")
        return redirect(url_for("admin_panel"))
    return render_template("editar_usuario.html", user_data=user)


# -----------------------------
# Dashboard
# -----------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    inventarios = Inventario.query.filter_by(empresa=empresa).all()
    inv_ids = [i.id for i in inventarios]
    todos_productos = Producto.query.filter(Producto.inventario_id.in_(inv_ids)).all() if inv_ids else []
    total = len(todos_productos)
    ultimos = Producto.query.filter(
        Producto.inventario_id.in_(inv_ids)
    ).order_by(Producto.creado_en.desc()).limit(5).all() if inv_ids else []
    cats = db.session.query(Producto.categoria).filter(
        Producto.inventario_id.in_(inv_ids),
        Producto.categoria != None,
        Producto.categoria != ""
    ).distinct().count() if inv_ids else 0
    campo_prov = CampoPersonalizado.query.filter_by(empresa=empresa, nombre="Proveedor").first()
    total_proveedores = 0
    if campo_prov:
        total_proveedores = db.session.query(ValorCampo.valor).filter(
            ValorCampo.campo_id==campo_prov.id,
            ValorCampo.valor != None,
            ValorCampo.valor != ""
        ).distinct().count()
    return render_template("dashboard.html",
                           usuario=session.get("username"),
                           total_productos=total,
                           total_categorias=cats,
                           total_proveedores=total_proveedores,
                           ultimos=ultimos)


# -----------------------------
# Inventario
# -----------------------------
@app.route("/inventario", methods=["GET", "POST"])
@app.route("/inventario/<int:inv_id>", methods=["GET", "POST"])
def inventario(inv_id=None):
    # Si no hay cat_id redirigir a categorias
    cat_id = request.args.get("cat") or request.form.get("cat_id")
    if not cat_id and request.method == "GET":
        if "user_id" not in session:
            return redirect(url_for("login"))
        user = Usuario.query.get(session["user_id"])
        empresa = user.empresa or ""
        inventarios = Inventario.query.filter_by(empresa=empresa).all()
        if not inventarios:
            return redirect(url_for("lista_inventarios"))
        inv_actual = Inventario.query.get(inv_id) if inv_id else inventarios[0]
        return redirect(url_for("categorias", inv_id=inv_actual.id))
    
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    inventarios = Inventario.query.filter_by(empresa=empresa).all()
    if not inventarios:
        flash("Crea un inventario primero.", "warning")
        return redirect(url_for("lista_inventarios"))
    inv_actual = Inventario.query.get(inv_id) if inv_id else inventarios[0]
    if not inv_actual or inv_actual.empresa != empresa:
        return redirect(url_for("inventario"))
    if request.method == "POST":
        nombre    = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "").strip()
        cantidad  = int(request.form.get("cantidad", 0))
        precio    = float(request.form.get("precio") or 0)
        unidad    = request.form.get("unidad", "unidad").strip()
        if not nombre:
            flash("Debe ingresar un nombre.", "warning")
        else:
            stock_minimo  = int(request.form.get("stock_minimo", 5))
            codigo_barras = request.form.get("codigo_barras", "").strip()
            p = Producto(user_id=session["user_id"], nombre=nombre,
                         categoria=categoria, cantidad=cantidad, precio=precio,
                         stock_minimo=stock_minimo, inventario_id=inv_actual.id,
                         codigo_barras=codigo_barras if codigo_barras else None)
            db.session.add(p)
            db.session.flush()
            campos = CampoPersonalizado.query.filter_by(inventario_id=inv_actual.id).all()
            for campo in campos:
                valor = request.form.get(f"campo_{campo.id}", "").strip()
                if valor:
                    db.session.add(ValorCampo(producto_id=p.id, campo_id=campo.id, valor=valor))
            db.session.commit()
            flash("Producto agregado.", "success")
    productos = Producto.query.filter_by(inventario_id=inv_actual.id).order_by(Producto.creado_en.desc()).all()
    campos = CampoPersonalizado.query.filter_by(inventario_id=inv_actual.id).all()
    categorias_inv = Categoria.query.filter_by(inventario_id=inv_actual.id).all()
    valores = {}
    for v in ValorCampo.query.all():
        valores.setdefault(v.producto_id, {})[v.campo_id] = v.valor
    return render_template("inventario.html", productos=productos, campos=campos,
                           valores=valores, inv_actual=inv_actual, inventarios=inventarios,
                           categorias_inv=categorias_inv)


@app.route("/inventario/editar/<int:producto_id>", methods=["GET", "POST"])
def inventario_editar(producto_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    prod = Producto.query.filter_by(
        id=producto_id, user_id=session["user_id"]).first()
    if not prod:
        flash("Producto no encontrado.", "danger")
        return redirect(url_for("inventario"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    campos = CampoPersonalizado.query.filter_by(empresa=empresa).all()
    if request.method == "POST":
        prod.nombre    = request.form.get("nombre", prod.nombre)
        prod.categoria = request.form.get("categoria", prod.categoria)
        prod.cantidad  = int(request.form.get("cantidad", prod.cantidad))
        prod.precio    = float(request.form.get("precio", prod.precio))
        prod.stock_minimo = int(request.form.get("stock_minimo", prod.stock_minimo or 5))
        for campo in campos:
            valor = request.form.get(f"campo_{campo.id}", "").strip()
            vc = ValorCampo.query.filter_by(producto_id=prod.id, campo_id=campo.id).first()
            if vc:
                vc.valor = valor
            elif valor:
                db.session.add(ValorCampo(producto_id=prod.id, campo_id=campo.id, valor=valor))
        db.session.commit()
        flash("Producto actualizado.", "success")
        return redirect(url_for("inventario"))
    valores = {v.campo_id: v.valor for v in ValorCampo.query.filter_by(producto_id=prod.id).all()}
    return render_template("inventario_editar.html", producto=prod, campos=campos, valores=valores)


@app.route("/inventario/eliminar/<int:producto_id>", methods=["POST", "GET"])
def inventario_eliminar(producto_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    prod = Producto.query.filter_by(
        id=producto_id, user_id=session["user_id"]).first()
    if prod:
        db.session.delete(prod)
        db.session.commit()
    flash("Producto eliminado.", "success")
    return redirect(url_for("inventario"))


# -----------------------------
# Mi empresa
# -----------------------------
@app.route("/mi_empresa")
def mi_empresa():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    usuarios = Usuario.query.filter_by(empresa=empresa).all()
    inventarios = Inventario.query.filter_by(empresa=empresa).all()
    return render_template("mi_empresa.html", empresa=empresa, user_data=user,
                           usuarios=usuarios, inventarios=inventarios)


@app.route("/usuarios_empresa")
def usuarios_empresa():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    usuarios = Usuario.query.filter_by(empresa=user.empresa).all()
    return render_template("usuarios_empresa.html", usuarios=usuarios)



# -----------------------------
# Campos personalizados
# -----------------------------
@app.route("/inventario/campos", methods=["GET", "POST"])
def campos_personalizados():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""

    if request.method == "POST":
        nombre  = request.form.get("nombre", "").strip()
        tipo    = request.form.get("tipo", "texto")
        opciones = request.form.get("opciones", "").strip()
        if nombre:
            inventario_id = request.form.get("inventario_id")
            campo = CampoPersonalizado(
                empresa=empresa, nombre=nombre, tipo=tipo, opciones=opciones,
                inventario_id=int(inventario_id) if inventario_id else None
            )
            db.session.add(campo)
            db.session.commit()
            flash(f"Campo '{nombre}' creado.", "success")
        redirect_url = request.form.get("redirect_url")
        if redirect_url:
            return redirect(redirect_url)
        return redirect(url_for("campos_personalizados"))

    campos = CampoPersonalizado.query.filter_by(empresa=empresa).all()
    return render_template("campos_personalizados.html", campos=campos)


@app.route("/inventario/campos/eliminar/<int:campo_id>")
def eliminar_campo(campo_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    campo = CampoPersonalizado.query.get(campo_id)
    if campo:
        db.session.delete(campo)
        db.session.commit()
        flash("Campo eliminado.", "success")
    return redirect(url_for("campos_personalizados"))



# -----------------------------

@app.route("/reportes")
def reportes():
    if "user_id" not in session:
        return redirect(url_for("login"))
    import datetime as dt
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    inventarios_emp = Inventario.query.filter_by(empresa=empresa).all()
    inv_ids = [i.id for i in inventarios_emp]
    productos = Producto.query.filter(Producto.inventario_id.in_(inv_ids)).all() if inv_ids else []
    total = len(productos)
    valor_total = sum(p.precio * p.cantidad for p in productos)
    sin_stock = sum(1 for p in productos if p.cantidad == 0)
    bajo_stock = sum(1 for p in productos if 0 < p.cantidad <= (p.stock_minimo or 5))
    alertas = [p for p in productos if p.cantidad <= (p.stock_minimo or 5)]
    cats = {}
    for p in productos:
        cat = p.categoria or "Sin categoria"
        cats[cat] = cats.get(cat, 0) + 1
    campos = CampoPersonalizado.query.filter_by(empresa=empresa).all()
    prods_mas_comprados = sorted(productos, key=lambda p: p.cantidad, reverse=True)[:5]
    prods_menos_comprados = sorted([p for p in productos if p.cantidad > 0], key=lambda p: p.cantidad)[:5]
    todas_ventas = Venta.query.filter_by(empresa=empresa).order_by(Venta.creado_en.desc()).all()
    venta_ids = [v.id for v in todas_ventas]
    items_vendidos = {}
    if venta_ids:
        items = VentaItem.query.filter(VentaItem.venta_id.in_(venta_ids)).all()
        for item in items:
            key = item.descripcion
            if key not in items_vendidos:
                items_vendidos[key] = {"cantidad": 0, "total": 0}
            items_vendidos[key]["cantidad"] += float(item.cantidad)
            items_vendidos[key]["total"] += float(item.total)
    prods_mas_vendidos = sorted(items_vendidos.items(), key=lambda x: x[1]["cantidad"], reverse=True)[:5]
    prods_menos_vendidos = sorted(items_vendidos.items(), key=lambda x: x[1]["cantidad"])[:5]
    today = dt.date.today()
    inicio_mes = today.replace(day=1)
    inicio_semana = today - dt.timedelta(days=today.weekday())
    ventas_hoy = [v for v in todas_ventas if v.creado_en.date() == today]
    ventas_semana = [v for v in todas_ventas if v.creado_en.date() >= inicio_semana]
    ventas_mes = [v for v in todas_ventas if v.creado_en.date() >= inicio_mes]
    total_hoy = sum(float(v.total) for v in ventas_hoy)
    total_semana = sum(float(v.total) for v in ventas_semana)
    total_mes = sum(float(v.total) for v in ventas_mes)
    total_general = sum(float(v.total) for v in todas_ventas)
    metodos = {}
    for v in todas_ventas:
        m = v.metodo_pago or "otro"
        metodos[m] = metodos.get(m, 0) + float(v.total)
    por_cliente = {}
    for v in todas_ventas:
        cl = v.cliente_nombre or "General"
        if cl not in por_cliente:
            por_cliente[cl] = {"total": 0, "count": 0}
        por_cliente[cl]["total"] += float(v.total)
        por_cliente[cl]["count"] += 1
    top_clientes = sorted(por_cliente.items(), key=lambda x: x[1]["total"], reverse=True)[:5]
    suscripciones = Suscripcion.query.filter_by(empresa=empresa).all()
    sus_activas = [s for s in suscripciones if s.estado == "activa"]
    sus_vencen_7 = [s for s in sus_activas if s.proximo_cobro and (s.proximo_cobro - today).days <= 7]
    sus_vencen_15 = [s for s in sus_activas if s.proximo_cobro and (s.proximo_cobro - today).days <= 15]
    sus_vencen_30 = [s for s in sus_activas if s.proximo_cobro and (s.proximo_cobro - today).days <= 30]
    ingreso_sus = sum(float(s.monto) for s in sus_activas)
    por_plan = {}
    for s in suscripciones:
        p = s.plan or "Sin plan"
        if p not in por_plan:
            por_plan[p] = {"count": 0, "ingreso": 0}
        por_plan[p]["count"] += 1
        por_plan[p]["ingreso"] += float(s.monto)
    planes_mas_vendidos = sorted(por_plan.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
    planes_menos_vendidos = sorted(por_plan.items(), key=lambda x: x[1]["count"])[:5]
    servicios = ServicioFijo.query.filter_by(empresa=empresa).all()
    srv_activos = [s for s in servicios if s.estado == "activo"]
    srv_vencidos = [s for s in servicios if s.estado != "activo" or (s.fecha_fin and s.fecha_fin < today)]
    ingreso_srv = sum(float(s.monto) for s in srv_activos)
    return render_template("reportes.html",
        total=total, valor_total=valor_total,
        sin_stock=sin_stock, bajo_stock=bajo_stock,
        alertas=alertas, categorias=cats, productos=productos, campos=campos,
        prods_mas_comprados=prods_mas_comprados,
        prods_menos_comprados=prods_menos_comprados,
        prods_mas_vendidos=prods_mas_vendidos,
        prods_menos_vendidos=prods_menos_vendidos,
        ventas_hoy=ventas_hoy, ventas_semana=ventas_semana, ventas_mes=ventas_mes,
        total_hoy=total_hoy, total_semana=total_semana,
        total_mes=total_mes, total_general=total_general,
        metodos=metodos, top_clientes=top_clientes,
        sus_activas=sus_activas, sus_vencen_7=sus_vencen_7,
        sus_vencen_15=sus_vencen_15, sus_vencen_30=sus_vencen_30,
        ingreso_sus=ingreso_sus,
        planes_mas_vendidos=planes_mas_vendidos,
        planes_menos_vendidos=planes_menos_vendidos,
        srv_activos=srv_activos, srv_vencidos=srv_vencidos,
        ingreso_srv=ingreso_srv, today=today)

@app.route("/reportes/campo/<int:campo_id>")
def reporte_por_campo(campo_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    campo = CampoPersonalizado.query.get(campo_id)
    if not campo:
        flash("Campo no encontrado.", "danger")
        return redirect(url_for("reportes"))
    valores = ValorCampo.query.filter_by(campo_id=campo_id).all()
    grupos = {}
    for v in valores:
        key = v.valor or "Sin valor"
        if key not in grupos:
            grupos[key] = []
        prod = Producto.query.get(v.producto_id)
        if prod and prod.user_id == session["user_id"]:
            grupos[key].append(prod)
    return render_template("reporte_campo.html", campo=campo, grupos=grupos)


@app.route("/reportes/exportar")
def exportar_csv():
    if "user_id" not in session:
        return redirect(url_for("login"))
    import csv
    import io
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    inventarios_emp = Inventario.query.filter_by(empresa=empresa).all()
    inv_ids = [i.id for i in inventarios_emp]
    productos = Producto.query.filter(Producto.inventario_id.in_(inv_ids)).all() if inv_ids else []
    campos = CampoPersonalizado.query.filter_by(empresa=empresa).all()
    valores = {}
    for v in ValorCampo.query.all():
        valores.setdefault(v.producto_id, {})[v.campo_id] = v.valor

    output = io.StringIO()
    writer = csv.writer(output)

    headers = ["ID", "Nombre", "Categoria", "Cantidad", "Precio", "Stock Minimo", "Valor Total", "Estado"]
    for campo in campos:
        headers.append(campo.nombre)
    writer.writerow(headers)

    for p in productos:
        estado = "Sin stock" if p.cantidad == 0 else ("Bajo stock" if p.cantidad <= (p.stock_minimo or 5) else "OK")
        row = [p.id, p.nombre, p.categoria or "", p.cantidad, p.precio, p.stock_minimo or 5, p.precio * p.cantidad, estado]
        for campo in campos:
            row.append(valores.get(p.id, {}).get(campo.id, ""))
        writer.writerow(row)

    output.seek(0)
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=inventario_{empresa}.csv"}
    )


@app.route("/reportes/enviar", methods=["POST"])
def enviar_reporte():
    if "user_id" not in session:
        return redirect(url_for("login"))
    import csv
    import io
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    email_destino = request.form.get("email_destino", "").strip()
    mensaje_extra = request.form.get("mensaje", "").strip()
    productos = Producto.query.filter_by(user_id=session["user_id"]).all()
    campos = CampoPersonalizado.query.filter_by(empresa=empresa).all()
    valores = {}
    for v in ValorCampo.query.all():
        valores.setdefault(v.producto_id, {})[v.campo_id] = v.valor

    output = io.StringIO()
    writer = csv.writer(output)
    headers = ["Nombre", "Categoria", "Cantidad", "Precio", "Stock Minimo", "Valor Total", "Estado"]
    for campo in campos:
        headers.append(campo.nombre)
    writer.writerow(headers)
    for p in productos:
        estado = "Sin stock" if p.cantidad == 0 else ("Bajo stock" if p.cantidad <= (p.stock_minimo or 5) else "OK")
        row = [p.nombre, p.categoria or "", p.cantidad, p.precio, p.stock_minimo or 5, p.precio * p.cantidad, estado]
        for campo in campos:
            row.append(valores.get(p.id, {}).get(campo.id, ""))
        writer.writerow(row)

    csv_content = output.getvalue()

    try:
        msg = Message(
            subject=f"Reporte de inventario — {empresa}",
            sender=app.config["MAIL_USERNAME"],
            recipients=[email_destino]
        )
        msg.body = f"{mensaje_extra}\n\nReporte generado desde aruna para {empresa}."
        msg.attach(f"inventario_{empresa}.csv", "text/csv", csv_content)
        mail.send(msg)
        flash(f"Reporte enviado a {email_destino}.", "success")
    except Exception as e:
        flash(f"Error al enviar el correo: {str(e)}", "danger")

    return redirect(url_for("reportes"))


# -----------------------------
# Multi-inventario
# -----------------------------
@app.route("/inventarios")
def lista_inventarios():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    inventarios = Inventario.query.filter_by(empresa=empresa).order_by(Inventario.creado_en).all()
    return render_template("inventarios.html", inventarios=inventarios)


@app.route("/inventarios/nuevo", methods=["GET", "POST"])
def nuevo_inventario():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        user = Usuario.query.get(session["user_id"])
        nombre       = request.form.get("nombre", "").strip().title()
        descripcion  = request.form.get("descripcion", "").strip()
        color        = request.form.get("color", "#561d9c")
        template_tipo = request.form.get("template_tipo", "general")
        inv = Inventario(
            empresa=user.empresa or "",
            nombre=nombre,
            descripcion=descripcion,
            color=color,
            creado_por=user.id
        )
        db.session.add(inv)
        db.session.flush()

        templates_campos = {
            "tecnologia":  [("Numero de serie","texto"),("Ubicacion","texto"),("Responsable","texto"),("Estado","dropdown"),("Recibido por","texto")],
            "restaurante": [("Unidad","dropdown"),("Proveedor","texto"),("Fecha de vencimiento","fecha"),("Recibido por","texto")],
            "taller":      [("Numero de serie","texto"),("Ubicacion","texto"),("Estado","dropdown"),("Ultimo mantenimiento","fecha"),("Responsable","texto")],
            "ropa":        [("Talla","texto"),("Color","texto"),("SKU","texto"),("Proveedor","texto")],
            "general":     []
        }
        opciones_estado = "Activo,En reparacion,De baja,En deposito"
        opciones_unidad = "kg,g,litros,ml,unidad,caja,paquete"
        for nombre_campo, tipo in templates_campos.get(template_tipo, []):
            opciones = ""
            if nombre_campo == "Estado": opciones = opciones_estado
            if nombre_campo == "Unidad": opciones = opciones_unidad
            campo = CampoPersonalizado(
                empresa=user.empresa or "",
                nombre=nombre_campo,
                tipo=tipo,
                opciones=opciones,
                inventario_id=inv.id
            )
            db.session.add(campo)
        db.session.commit()
        flash(f"Inventario '{nombre}' creado con campos de template {template_tipo}.", "success")
        return redirect(url_for("lista_inventarios"))
    return render_template("nuevo_inventario.html")


@app.route("/inventarios/<int:inv_id>/eliminar", methods=["POST"])
def eliminar_inventario(inv_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    if not user.empresa_admin:
        flash("No tienes permisos para eliminar inventarios.", "danger")
        return redirect(url_for("lista_inventarios"))
    inv = Inventario.query.get(inv_id)
    if not inv:
        return redirect(url_for("lista_inventarios"))
    if inv.productos:
        flash("No puedes eliminar un inventario con productos.", "warning")
        return redirect(url_for("lista_inventarios"))
    # Eliminar campos personalizados y categorias asociadas
    CampoPersonalizado.query.filter_by(inventario_id=inv_id).delete()
    Categoria.query.filter_by(inventario_id=inv_id).delete()
    db.session.delete(inv)
    db.session.commit()
    flash("Inventario eliminado.", "success")
    return redirect(url_for("lista_inventarios"))


@app.route("/empresa/cambiar_rol/<int:user_id>", methods=["POST"])
def cambiar_rol(user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    admin = Usuario.query.get(session["user_id"])
    if not admin.empresa_admin:
        flash("No tienes permisos para cambiar roles.", "danger")
        return redirect(url_for("mi_empresa"))
    user = Usuario.query.get(user_id)
    if not user or user.empresa != admin.empresa:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("mi_empresa"))
    if user.empresa_admin:
        flash("No puedes cambiar el rol del administrador principal.", "warning")
        return redirect(url_for("mi_empresa"))
    nuevo_rol = request.form.get("rol", "viewer")
    if nuevo_rol not in ["viewer", "editor"]:
        nuevo_rol = "viewer"
    user.rol = nuevo_rol
    db.session.commit()
    flash(f"Rol de {user.nombre} actualizado a {nuevo_rol}.", "success")
    return redirect(url_for("mi_empresa"))


@app.route("/empresa/invitar", methods=["POST"])
def invitar_usuario():
    if "user_id" not in session:
        return redirect(url_for("login"))
    admin = Usuario.query.get(session["user_id"])
    if not admin.empresa_admin:
        flash("No tienes permisos para invitar usuarios.", "danger")
        return redirect(url_for("mi_empresa"))
    email_invitado = request.form.get("email_invitado", "").strip()
    if not email_invitado:
        flash("Ingresa un correo válido.", "warning")
        return redirect(url_for("mi_empresa"))
    import hashlib, time
    token = hashlib.sha256(f"{email_invitado}{admin.empresa}{time.time()}".encode()).hexdigest()[:32]
    try:
        msg = Message(
            subject=f"Invitación a unirse a {admin.empresa} en aruna",
            sender=app.config["MAIL_USERNAME"],
            recipients=[email_invitado]
        )
        link = url_for("registro_invitado", token=token,
                       empresa=admin.empresa, correo=email_invitado, _external=True)
        msg.body = (
            f"Hola,\n\n"
            f"{admin.nombre} {admin.apellido} te invita a unirte a {admin.empresa} en aruna.\n\n"
            f"Completa tu registro aquí:\n{link}\n\n"
            f"Este enlace expira en 48 horas.\n\n"
            f"— Equipo aruna"
        )
        mail.send(msg)
        flash(f"Invitación enviada a {email_invitado}.", "success")
    except Exception as e:
        flash(f"Error al enviar invitación: {str(e)}", "danger")
    return redirect(url_for("mi_empresa"))


@app.route("/registro/invitado", methods=["GET", "POST"])
def registro_invitado():
    empresa = request.args.get("empresa", "")
    correo  = request.args.get("correo", "")
    token   = request.args.get("token", "")
    if request.method == "POST":
        empresa = request.form.get("empresa", "")
        correo  = request.form.get("correo", "")
        nombre   = request.form.get("nombre", "").strip().title()
        apellido = request.form.get("apellido", "").strip().title()
        telefono = request.form.get("telefono", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        if password != confirm:
            flash("Las contraseñas no coinciden.", "warning")
            return render_template("registro_invitado.html", empresa=empresa, correo=correo, token=token)
        ok, msg = password_valid(password)
        if not ok:
            flash(msg, "warning")
            return render_template("registro_invitado.html", empresa=empresa, correo=correo, token=token)
        if Usuario.query.filter_by(username=username).first():
            flash("Ese nombre de usuario ya existe.", "danger")
            return render_template("registro_invitado.html", empresa=empresa, correo=correo, token=token)
        user = Usuario(
            nombre=nombre, apellido=apellido, empresa=empresa,
            correo=correo, telefono=telefono, username=username,
            password=generate_password_hash(password),
            verificado=1, rol="viewer", empresa_admin=False
        )
        db.session.add(user)
        db.session.commit()
        flash("Cuenta creada exitosamente. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("login"))
    return render_template("registro_invitado.html", empresa=empresa, correo=correo, token=token)


@app.route("/producto/<int:producto_id>/qr")
def generar_qr(producto_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    import qrcode
    import io
    prod = Producto.query.get(producto_id)
    if not prod:
        return "Producto no encontrado", 404
    url = url_for("ficha_producto", producto_id=producto_id, _external=True)
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    from flask import send_file
    return send_file(buf, mimetype="image/png")


@app.route("/producto/<int:producto_id>/ficha")
def ficha_producto(producto_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    prod = Producto.query.get(producto_id)
    if not prod:
        return "Producto no encontrado", 404
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    campos = CampoPersonalizado.query.filter_by(inventario_id=prod.inventario_id).all()
    valores = {v.campo_id: v.valor for v in ValorCampo.query.filter_by(producto_id=prod.id).all()}
    inv = Inventario.query.get(prod.inventario_id)
    return render_template("ficha_producto.html", producto=prod, campos=campos, valores=valores, inventario=inv)


@app.route("/inventario/<int:inv_id>/escanear")
def escanear(inv_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    inv = Inventario.query.get(inv_id)
    return render_template("escanear.html", inv=inv)


@app.route("/inventario/buscar_codigo")
def buscar_codigo():
    if "user_id" not in session:
        return jsonify({"error": "no auth"}), 401
    codigo = request.args.get("codigo", "").strip()
    prod = Producto.query.filter_by(codigo_barras=codigo).first()
    if prod:
        return jsonify({
            "encontrado": True,
            "id": prod.id,
            "nombre": prod.nombre,
            "cantidad": prod.cantidad,
            "categoria": prod.categoria or "",
            "url": url_for("ficha_producto", producto_id=prod.id)
        })
    return jsonify({"encontrado": False})


# -----------------------------
# Categorias
# -----------------------------
@app.route("/inventario/<int:inv_id>/categorias")
def categorias(inv_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    inv = Inventario.query.get(inv_id)
    cats = Categoria.query.filter_by(inventario_id=inv_id).all()
    return render_template("categorias.html", inv=inv, categorias=cats)


@app.route("/inventario/<int:inv_id>/categorias/nueva", methods=["GET","POST"])
def nueva_categoria(inv_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    inv = Inventario.query.get(inv_id)
    if request.method == "POST":
        nombre      = request.form.get("nombre","").strip().title()
        descripcion = request.form.get("descripcion","").strip()
        tipo        = request.form.get("tipo","stock")
        stock_min   = int(request.form.get("stock_minimo", 5)) if tipo == "stock" else 0
        color       = request.form.get("color","#561d9c")
        cat = Categoria(inventario_id=inv_id, nombre=nombre, descripcion=descripcion,
                        tipo=tipo, stock_minimo=stock_min, color=color)
        db.session.add(cat)
        db.session.commit()
        flash(f"Categoria '{nombre}' creada.", "success")
        return redirect(url_for("categorias", inv_id=inv_id))
    return render_template("nueva_categoria.html", inv=inv)


@app.route("/inventario/<int:inv_id>/categorias/<int:cat_id>/eliminar", methods=["POST"])
def eliminar_categoria(inv_id, cat_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    cat = Categoria.query.get(cat_id)
    if cat and len(cat.productos) == 0:
        db.session.delete(cat)
        db.session.commit()
        flash("Categoria eliminada.", "success")
    else:
        flash("No puedes eliminar una categoria con productos.", "warning")
    return redirect(url_for("categorias", inv_id=inv_id))


@app.route("/inventario/<int:inv_id>/categoria/<int:cat_id>", methods=["GET", "POST"])
def productos_categoria(inv_id, cat_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    inv = Inventario.query.get(inv_id)
    cat = Categoria.query.get(cat_id)
    if not inv or not cat:
        return redirect(url_for("lista_inventarios"))

    if request.method == "POST":
        nombre        = request.form.get("nombre", "").strip()
        precio        = float(request.form.get("precio") or 0)
        codigo_barras = request.form.get("codigo_barras", "").strip()
        if cat.tipo == "activo":
            cantidad     = 1
            stock_minimo = 0
        else:
            cantidad     = int(request.form.get("cantidad", 0))
            stock_minimo = int(request.form.get("stock_minimo", cat.stock_minimo or 5))

        if nombre:
            p = Producto(
                user_id=session["user_id"],
                nombre=nombre,
                categoria=cat.nombre,
                categoria_id=cat_id,
                cantidad=cantidad,
                precio=precio,
                stock_minimo=stock_minimo,
                inventario_id=inv_id,
                codigo_barras=codigo_barras if codigo_barras else None
            )
            db.session.add(p)
            db.session.flush()
            campos = CampoPersonalizado.query.filter_by(inventario_id=inv_id).all()
            for campo in campos:
                valor = request.form.get(f"campo_{campo.id}", "").strip()
                if valor:
                    db.session.add(ValorCampo(producto_id=p.id, campo_id=campo.id, valor=valor))
            db.session.commit()
            flash("Producto agregado.", "success")
        return redirect(url_for("productos_categoria", inv_id=inv_id, cat_id=cat_id))

    productos = Producto.query.filter_by(inventario_id=inv_id, categoria_id=cat_id).order_by(Producto.creado_en.desc()).all()
    campos = CampoPersonalizado.query.filter_by(inventario_id=inv_id).all()
    valores = {}
    for v in ValorCampo.query.all():
        valores.setdefault(v.producto_id, {})[v.campo_id] = v.valor
    return render_template("productos_categoria.html",
        inv=inv, cat=cat, productos=productos,
        campos=campos, valores=valores)



# -----------------------------
# Modulo de Ventas
# -----------------------------
@app.route("/ventas")
def ventas():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    ventas = Venta.query.filter_by(empresa=empresa).order_by(Venta.creado_en.desc()).all()
    suscripciones = Suscripcion.query.filter_by(empresa=empresa).order_by(Suscripcion.creado_en.desc()).all()
    servicios = ServicioFijo.query.filter_by(empresa=empresa).order_by(ServicioFijo.creado_en.desc()).all()
    clientes = Cliente.query.filter_by(empresa=empresa).all()
    total_ventas = sum(float(v.total) for v in ventas)
    total_suscripciones = sum(float(s.monto) for s in suscripciones if s.estado == "activa")
    total_servicios = sum(float(s.monto) for s in servicios if s.estado == "activo")
    import datetime as dt
    return render_template("ventas.html",
        ventas=ventas, suscripciones=suscripciones, servicios=servicios,
        clientes=clientes, total_ventas=total_ventas,
        total_suscripciones=total_suscripciones, total_servicios=total_servicios,
        today=dt.date.today())


@app.route("/ventas/clientes")
def clientes():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    clientes = Cliente.query.filter_by(empresa=empresa).order_by(Cliente.creado_en.desc()).all()
    return render_template("clientes.html", clientes=clientes)


@app.route("/ventas/clientes/nuevo", methods=["GET","POST"])
def nuevo_cliente():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    if request.method == "POST":
        tipo_cliente = request.form.get("tipo_cliente","natural")
        if tipo_cliente == "legal":
            nombre   = request.form.get("nombre","").strip().title()
            apellido = request.form.get("apellido","").strip().title()
            ruc      = request.form.get("ruc","").strip()
            dv       = request.form.get("dv","").strip()
            correo   = request.form.get("correo_empresa","").strip() or request.form.get("correo","").strip()
            telefono = request.form.get("telefono_empresa","").strip() or request.form.get("telefono","").strip()
            razon_social = request.form.get("razon_social","").strip().title()
            direccion = razon_social
        else:
            nombre   = request.form.get("nombre","").strip().title()
            apellido = request.form.get("apellido","").strip().title()
            ruc      = request.form.get("cedula","").strip()
            dv       = ""
            correo   = request.form.get("correo","").strip()
            telefono = request.form.get("telefono","").strip()
            direccion = request.form.get("direccion","").strip()

        cl = Cliente(
            empresa=user.empresa or "",
            nombre=nombre, apellido=apellido,
            ruc=ruc, dv=dv, correo=correo,
            telefono=telefono, direccion=direccion
        )
        db.session.add(cl)
        db.session.commit()
        flash(f"Cliente {cl.nombre} registrado.", "success")
        return redirect(url_for("clientes"))
    return render_template("nuevo_cliente.html")


@app.route("/ventas/nueva", methods=["GET","POST"])
def nueva_venta():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    clientes = Cliente.query.filter_by(empresa=empresa).all()
    inventarios = Inventario.query.filter_by(empresa=empresa).all()
    inv_ids = [i.id for i in inventarios]
    productos = Producto.query.filter(Producto.inventario_id.in_(inv_ids)).all() if inv_ids else []

    if request.method == "POST":
        import datetime as dt
        cliente_id   = request.form.get("cliente_id") or None
        cliente_nombre = request.form.get("cliente_nombre","").strip()
        cliente_ruc  = request.form.get("cliente_ruc","").strip()
        cliente_correo = request.form.get("cliente_correo","").strip()
        documento    = request.form.get("documento","recibo")
        metodo_pago  = request.form.get("metodo_pago","efectivo")
        descuento    = float(request.form.get("descuento",0) or 0)
        aplicar_itbms = request.form.get("aplicar_itbms") == "1"
        notas        = request.form.get("notas","").strip()

        if cliente_id:
            cl = Cliente.query.get(int(cliente_id))
            if cl:
                cliente_nombre = f"{cl.nombre} {cl.apellido or ''}".strip()
                cliente_ruc    = cl.ruc or ""
                cliente_correo = cl.correo or ""

        # Generar numero de factura
        ultimo = Venta.query.filter_by(empresa=empresa).order_by(Venta.id.desc()).first()
        num = (ultimo.id + 1) if ultimo else 1
        numero_factura = f"{'FAC' if documento == 'factura' else 'REC'}-{str(num).zfill(5)}"

        # Procesar items
        nombres = request.form.getlist("item_nombre[]")
        cantidades = request.form.getlist("item_cantidad[]")
        precios = request.form.getlist("item_precio[]")
        producto_ids = request.form.getlist("item_producto_id[]")

        subtotal = 0
        items_data = []
        for i in range(len(nombres)):
            if nombres[i].strip():
                cant = float(cantidades[i] or 1)
                precio = float(precios[i] or 0)
                total_item = cant * precio
                subtotal += total_item
                items_data.append({
                    "descripcion": nombres[i].strip(),
                    "cantidad": cant,
                    "precio_unitario": precio,
                    "total": total_item,
                    "producto_id": int(producto_ids[i]) if producto_ids[i] else None
                })

        subtotal -= descuento
        itbms = round(subtotal * 0.07, 2) if aplicar_itbms else 0
        total = subtotal + itbms

        venta = Venta(
            empresa=empresa, tipo="venta",
            numero_factura=numero_factura,
            cliente_id=int(cliente_id) if cliente_id else None,
            cliente_nombre=cliente_nombre,
            cliente_ruc=cliente_ruc,
            cliente_correo=cliente_correo,
            subtotal=subtotal, itbms=itbms,
            descuento=descuento, total=total,
            metodo_pago=metodo_pago, documento=documento,
            notas=notas, creado_por=user.id
        )
        db.session.add(venta)
        db.session.flush()

        for item in items_data:
            vi = VentaItem(
                venta_id=venta.id,
                producto_id=item["producto_id"],
                descripcion=item["descripcion"],
                cantidad=item["cantidad"],
                precio_unitario=item["precio_unitario"],
                total=item["total"]
            )
            db.session.add(vi)
            if item["producto_id"]:
                prod = Producto.query.get(item["producto_id"])
                if prod:
                    prod.cantidad = max(0, prod.cantidad - int(item["cantidad"]))

        db.session.commit()
        flash(f"Venta {numero_factura} registrada.", "success")
        return redirect(url_for("ver_venta", venta_id=venta.id))

    return render_template("nueva_venta.html", clientes=clientes, productos=productos)


@app.route("/ventas/<int:venta_id>")
def ver_venta(venta_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    venta = Venta.query.get(venta_id)
    user = Usuario.query.get(session["user_id"])
    return render_template("ver_venta.html", venta=venta, empresa=user)


@app.route("/ventas/suscripcion/nueva", methods=["GET","POST"])
def nueva_suscripcion():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    clientes = Cliente.query.filter_by(empresa=empresa).all()
    if request.method == "POST":
        import datetime as dt
        cliente_id = request.form.get("cliente_id") or None
        cliente_nombre = request.form.get("cliente_nombre","").strip()
        if cliente_id:
            cl = Cliente.query.get(int(cliente_id))
            if cl: cliente_nombre = f"{cl.nombre} {cl.apellido or ''}".strip()
        fecha_inicio = dt.date.fromisoformat(request.form.get("fecha_inicio"))
        frecuencia = request.form.get("frecuencia","mensual")
        from dateutil.relativedelta import relativedelta
        freq_map = {"semanal":relativedelta(weeks=1),"mensual":relativedelta(months=1),"trimestral":relativedelta(months=3),"anual":relativedelta(years=1)}
        proximo = fecha_inicio + freq_map.get(frecuencia, relativedelta(months=1))
        s = Suscripcion(
            empresa=empresa,
            cliente_id=int(cliente_id) if cliente_id else None,
            cliente_nombre=cliente_nombre,
            plan=request.form.get("plan","").strip(),
            descripcion=request.form.get("descripcion","").strip(),
            monto=float(request.form.get("monto",0)),
            frecuencia=frecuencia,
            fecha_inicio=fecha_inicio,
            proximo_cobro=proximo,
            metodo_pago=request.form.get("metodo_pago","efectivo"),
            creado_por=user.id
        )
        db.session.add(s)
        db.session.commit()
        flash("Suscripcion registrada.", "success")
        return redirect(url_for("ventas"))
    return render_template("nueva_suscripcion.html", clientes=clientes)


@app.route("/ventas/servicio/nuevo", methods=["GET","POST"])
def nuevo_servicio():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    clientes = Cliente.query.filter_by(empresa=empresa).all()
    if request.method == "POST":
        import datetime as dt
        cliente_id = request.form.get("cliente_id") or None
        cliente_nombre = request.form.get("cliente_nombre","").strip()
        if cliente_id:
            cl = Cliente.query.get(int(cliente_id))
            if cl: cliente_nombre = f"{cl.nombre} {cl.apellido or ''}".strip()
        s = ServicioFijo(
            empresa=empresa,
            cliente_id=int(cliente_id) if cliente_id else None,
            cliente_nombre=cliente_nombre,
            descripcion=request.form.get("descripcion","").strip(),
            monto=float(request.form.get("monto",0)),
            periodo=request.form.get("periodo","mensual"),
            fecha_inicio=dt.date.fromisoformat(request.form.get("fecha_inicio")),
            fecha_fin=dt.date.fromisoformat(request.form.get("fecha_fin")) if request.form.get("fecha_fin") else None,
            metodo_pago=request.form.get("metodo_pago","efectivo"),
            creado_por=user.id
        )
        db.session.add(s)
        db.session.commit()
        flash("Servicio registrado.", "success")
        return redirect(url_for("ventas"))
    return render_template("nuevo_servicio.html", clientes=clientes)


# -----------------------------
# Planes / Catalogo
# -----------------------------
@app.route("/ventas/planes")
def planes():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    planes = Plan.query.filter_by(empresa=empresa).order_by(Plan.creado_en.desc()).all()
    return render_template("planes.html", planes=planes)


@app.route("/ventas/planes/nuevo", methods=["GET","POST"])
def nuevo_plan():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    if request.method == "POST":
        import datetime as dt
        nombre      = request.form.get("nombre","").strip().title()
        descripcion = request.form.get("descripcion","").strip()
        costo       = float(request.form.get("costo", 0))
        frecuencia  = request.form.get("frecuencia","mensual")
        color       = request.form.get("color","#561d9c")

        plan = Plan(empresa=empresa, nombre=nombre, descripcion=descripcion,
                    costo=costo, frecuencia=frecuencia, color=color)
        db.session.add(plan)
        db.session.flush()

        # Items que incluye
        incluye_items = request.form.getlist("incluye[]")
        for item in incluye_items:
            if item.strip():
                db.session.add(PlanIncluye(plan_id=plan.id, descripcion=item.strip()))

        # Horarios
        dias       = request.form.getlist("horario_dia[]")
        inicios    = request.form.getlist("horario_inicio[]")
        fines      = request.form.getlist("horario_fin[]")
        actividades= request.form.getlist("horario_actividad[]")
        instructores = request.form.getlist("horario_instructor[]")

        for i in range(len(dias)):
            if dias[i] and inicios[i] and fines[i] and actividades[i]:
                db.session.add(PlanHorario(
                    plan_id=plan.id,
                    dia=dias[i],
                    hora_inicio=dt.time.fromisoformat(inicios[i]),
                    hora_fin=dt.time.fromisoformat(fines[i]),
                    actividad=actividades[i].strip(),
                    instructor=instructores[i].strip() if i < len(instructores) else ""
                ))

        db.session.commit()
        flash(f"Plan '{nombre}' creado.", "success")
        return redirect(url_for("planes"))
    return render_template("nuevo_plan.html")


@app.route("/ventas/planes/<int:plan_id>")
def ver_plan(plan_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    plan = Plan.query.get(plan_id)
    suscriptores = Suscripcion.query.filter_by(plan_id=plan_id).all()
    return render_template("ver_plan.html", plan=plan, suscriptores=suscriptores)


@app.route("/ventas/planes/<int:plan_id>/toggle")
def toggle_plan(plan_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    plan = Plan.query.get(plan_id)
    if plan:
        plan.activo = not plan.activo
        db.session.commit()
        flash(f"Plan {'activado' if plan.activo else 'desactivado'}.", "success")
    return redirect(url_for("planes"))


@app.route("/ventas/planes/api")
def api_planes():
    if "user_id" not in session:
        return jsonify([])
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    planes = Plan.query.filter_by(empresa=empresa, activo=True).all()
    return jsonify([{
        "id": p.id, "nombre": p.nombre, "costo": float(p.costo),
        "frecuencia": p.frecuencia, "descripcion": p.descripcion or ""
    } for p in planes])


@app.route("/ventas/planes/<int:plan_id>/editar", methods=["GET","POST"])
def editar_plan(plan_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    plan = Plan.query.get(plan_id)
    if not plan:
        return redirect(url_for("planes"))
    if request.method == "POST":
        import datetime as dt
        plan.nombre      = request.form.get("nombre","").strip().title()
        plan.descripcion = request.form.get("descripcion","").strip()
        plan.costo       = float(request.form.get("costo", plan.costo))
        plan.frecuencia  = request.form.get("frecuencia", plan.frecuencia)
        plan.color       = request.form.get("color", plan.color)

        # Actualizar incluye
        PlanIncluye.query.filter_by(plan_id=plan.id).delete()
        for item in request.form.getlist("incluye[]"):
            if item.strip():
                db.session.add(PlanIncluye(plan_id=plan.id, descripcion=item.strip()))

        # Actualizar horarios
        PlanHorario.query.filter_by(plan_id=plan.id).delete()
        dias        = request.form.getlist("horario_dia[]")
        inicios     = request.form.getlist("horario_inicio[]")
        fines       = request.form.getlist("horario_fin[]")
        actividades = request.form.getlist("horario_actividad[]")
        instructores= request.form.getlist("horario_instructor[]")
        for i in range(len(dias)):
            if dias[i] and inicios[i] and fines[i] and actividades[i]:
                db.session.add(PlanHorario(
                    plan_id=plan.id,
                    dia=dias[i],
                    hora_inicio=dt.time.fromisoformat(inicios[i]),
                    hora_fin=dt.time.fromisoformat(fines[i]),
                    actividad=actividades[i].strip(),
                    instructor=instructores[i].strip() if i < len(instructores) else ""
                ))
        db.session.commit()
        flash(f"Plan actualizado.", "success")
        return redirect(url_for("planes"))
    return render_template("editar_plan.html", plan=plan)


@app.route("/empresa/eliminar_usuario/<int:user_id>", methods=["POST"])
def eliminar_usuario_empresa(user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    admin = Usuario.query.get(session["user_id"])
    if not admin.empresa_admin:
        flash("No tienes permisos.", "danger")
        return redirect(url_for("mi_empresa"))
    user = Usuario.query.get(user_id)
    if not user or user.empresa != admin.empresa:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("mi_empresa"))
    if user.empresa_admin:
        flash("No puedes eliminar al administrador principal.", "warning")
        return redirect(url_for("mi_empresa"))
    db.session.delete(user)
    db.session.commit()
    flash(f"Usuario {user.nombre} eliminado.", "success")
    return redirect(url_for("mi_empresa"))


@app.route("/empresa/configurar_timeout", methods=["POST"])
def configurar_timeout():
    if "user_id" not in session:
        return redirect(url_for("login"))
    admin = Usuario.query.get(session["user_id"])
    if not admin.empresa_admin:
        flash("No tienes permisos.", "danger")
        return redirect(url_for("mi_empresa"))
    timeout = int(request.form.get("session_timeout", 120))
    if timeout < 15: timeout = 15
    if timeout > 480: timeout = 480
    # Aplicar a todos los usuarios de la empresa
    usuarios = Usuario.query.filter_by(empresa=admin.empresa).all()
    for u in usuarios:
        u.session_timeout = timeout
    db.session.commit()
    flash(f"Tiempo de sesion actualizado a {timeout} minutos.", "success")
    return redirect(url_for("mi_empresa"))


@app.route("/empresa/editar_usuario/<int:user_id>", methods=["GET","POST"])
def editar_usuario_empresa(user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    admin = Usuario.query.get(session["user_id"])
    if not admin.empresa_admin:
        flash("No tienes permisos.", "danger")
        return redirect(url_for("mi_empresa"))
    user = Usuario.query.get(user_id)
    if not user or user.empresa != admin.empresa:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("mi_empresa"))
    if request.method == "POST":
        user.nombre   = request.form.get("nombre", user.nombre).strip().title()
        user.apellido = request.form.get("apellido", user.apellido).strip().title()
        user.correo   = request.form.get("correo", user.correo).strip()
        user.telefono = request.form.get("telefono", user.telefono).strip()
        db.session.commit()
        flash("Usuario actualizado.", "success")
        return redirect(url_for("mi_empresa"))
    return render_template("editar_usuario_empresa.html", user_data=user)



# -----------------------------
# CRM
# -----------------------------
@app.route("/crm")
def crm():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    import datetime as dt
    today = dt.date.today()
    contactos = CrmContacto.query.filter_by(empresa_id=empresa).order_by(CrmContacto.creado_en.desc()).all()
    oportunidades = CrmOportunidad.query.filter_by(empresa_id=empresa).all()
    tareas = CrmTarea.query.filter_by(empresa_id=empresa).order_by(CrmTarea.fecha_limite).all()
    tareas_pendientes = [t for t in tareas if t.estado == "pendiente"]
    tareas_vencidas = [t for t in tareas_pendientes if t.fecha_limite and t.fecha_limite < today]
    pipeline = {
        "prospecto":   [o for o in oportunidades if o.etapa == "prospecto"],
        "contactado":  [o for o in oportunidades if o.etapa == "contactado"],
        "propuesta":   [o for o in oportunidades if o.etapa == "propuesta"],
        "negociacion": [o for o in oportunidades if o.etapa == "negociacion"],
        "cerrado":     [o for o in oportunidades if o.etapa == "cerrado"],
        "perdido":     [o for o in oportunidades if o.etapa == "perdido"],
    }
    valor_pipeline = sum(float(o.valor) for o in oportunidades if o.etapa not in ["cerrado","perdido"])
    valor_cerrado  = sum(float(o.valor) for o in oportunidades if o.etapa == "cerrado")
    return render_template("crm.html",
        contactos=contactos, oportunidades=oportunidades,
        tareas=tareas, tareas_pendientes=tareas_pendientes,
        tareas_vencidas=tareas_vencidas, pipeline=pipeline,
        valor_pipeline=valor_pipeline, valor_cerrado=valor_cerrado,
        today=today)


@app.route("/crm/contactos/nuevo", methods=["GET","POST"])
def crm_nuevo_contacto():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    if request.method == "POST":
        c = CrmContacto(
            empresa_id=user.empresa or "",
            nombre=request.form.get("nombre","").strip().title(),
            apellido=request.form.get("apellido","").strip().title(),
            empresa_contacto=request.form.get("empresa_contacto","").strip().title(),
            cargo=request.form.get("cargo","").strip(),
            correo=request.form.get("correo","").strip(),
            telefono=request.form.get("telefono","").strip(),
            origen=request.form.get("origen",""),
            notas=request.form.get("notas","").strip(),
            creado_por=user.id
        )
        db.session.add(c)
        db.session.commit()
        flash(f"Contacto {c.nombre} creado.", "success")
        return redirect(url_for("crm"))
    return render_template("crm_nuevo_contacto.html")


@app.route("/crm/contactos/<int:contacto_id>")
def crm_ver_contacto(contacto_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    contacto = CrmContacto.query.get(contacto_id)
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    usuarios_empresa = Usuario.query.filter_by(empresa=empresa).all()
    return render_template("crm_ver_contacto.html", contacto=contacto,
        usuarios_empresa=usuarios_empresa)


@app.route("/crm/contactos/<int:contacto_id>/interaccion", methods=["POST"])
def crm_nueva_interaccion(contacto_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    i = CrmInteraccion(
        contacto_id=contacto_id,
        tipo=request.form.get("tipo","nota"),
        descripcion=request.form.get("descripcion","").strip(),
        resultado=request.form.get("resultado","").strip(),
        creado_por=user.id
    )
    db.session.add(i)
    db.session.commit()
    flash("Interaccion registrada.", "success")
    return redirect(url_for("crm_ver_contacto", contacto_id=contacto_id))


@app.route("/crm/oportunidades/nueva", methods=["GET","POST"])
def crm_nueva_oportunidad():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    contactos = CrmContacto.query.filter_by(empresa_id=empresa).all()
    usuarios_empresa = Usuario.query.filter_by(empresa=empresa).all()
    if request.method == "POST":
        import datetime as dt
        o = CrmOportunidad(
            empresa_id=empresa,
            contacto_id=int(request.form.get("contacto_id")) if request.form.get("contacto_id") else None,
            titulo=request.form.get("titulo","").strip(),
            valor=float(request.form.get("valor",0) or 0),
            etapa=request.form.get("etapa","prospecto"),
            responsable_id=int(request.form.get("responsable_id")) if request.form.get("responsable_id") else user.id,
            fecha_cierre=dt.date.fromisoformat(request.form.get("fecha_cierre")) if request.form.get("fecha_cierre") else None,
            probabilidad=int(request.form.get("probabilidad",0) or 0),
            notas=request.form.get("notas","").strip()
        )
        db.session.add(o)
        db.session.commit()
        flash("Oportunidad creada.", "success")
        return redirect(url_for("crm"))
    return render_template("crm_nueva_oportunidad.html",
        contactos=contactos, usuarios_empresa=usuarios_empresa)


@app.route("/crm/oportunidades/<int:op_id>/etapa", methods=["POST"])
def crm_cambiar_etapa(op_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    op = CrmOportunidad.query.get(op_id)
    if op:
        op.etapa = request.form.get("etapa", op.etapa)
        db.session.commit()
    return redirect(url_for("crm"))


@app.route("/crm/tareas/nueva", methods=["POST"])
def crm_nueva_tarea():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    import datetime as dt
    t = CrmTarea(
        empresa_id=user.empresa or "",
        contacto_id=int(request.form.get("contacto_id")) if request.form.get("contacto_id") else None,
        oportunidad_id=int(request.form.get("oportunidad_id")) if request.form.get("oportunidad_id") else None,
        descripcion=request.form.get("descripcion","").strip(),
        asignado_a=int(request.form.get("asignado_a")) if request.form.get("asignado_a") else user.id,
        fecha_limite=dt.date.fromisoformat(request.form.get("fecha_limite")) if request.form.get("fecha_limite") else None,
        prioridad=request.form.get("prioridad","media"),
        creado_por=user.id
    )
    db.session.add(t)
    db.session.commit()
    flash("Tarea creada.", "success")
    return redirect(request.referrer or url_for("crm"))


@app.route("/crm/tareas/<int:tarea_id>/completar", methods=["POST"])
def crm_completar_tarea(tarea_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    tarea = CrmTarea.query.get(tarea_id)
    if tarea:
        tarea.estado = "completada"
        db.session.commit()
        flash("Tarea completada.", "success")
    return redirect(request.referrer or url_for("crm"))


# -----------------------------
# Flujos / Workflow Engine
# -----------------------------
@app.route("/flujos")
def lista_flujos():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    flujos = Flujo.query.filter_by(empresa=empresa).order_by(Flujo.creado_en.desc()).all()
    return render_template("flujos.html", flujos=flujos)


@app.route("/flujos/nuevo", methods=["GET","POST"])
def nuevo_flujo():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    usuarios_empresa = Usuario.query.filter_by(empresa=empresa).all()
    if request.method == "POST":
        nombre      = request.form.get("nombre","").strip()
        modulo      = request.form.get("modulo","crm")
        descripcion = request.form.get("descripcion","").strip()
        flujo = Flujo(empresa=empresa, nombre=nombre, modulo=modulo, descripcion=descripcion)
        db.session.add(flujo)
        db.session.flush()

        nombres_etapa   = request.form.getlist("etapa_nombre[]")
        colores_etapa   = request.form.getlist("etapa_color[]")
        resp_etapa      = request.form.getlist("etapa_responsable[]")
        final_etapa     = request.form.getlist("etapa_final[]")
        perdido_etapa   = request.form.getlist("etapa_perdido[]")

        for i, nombre_e in enumerate(nombres_etapa):
            if nombre_e.strip():
                etapa = FlujoEtapa(
                    flujo_id=flujo.id,
                    nombre=nombre_e.strip(),
                    color=colores_etapa[i] if i < len(colores_etapa) else "#561d9c",
                    orden=i,
                    responsable_id=int(resp_etapa[i]) if i < len(resp_etapa) and resp_etapa[i] else None,
                    es_final=str(i) in final_etapa,
                    es_perdido=str(i) in perdido_etapa
                )
                db.session.add(etapa)

        db.session.commit()
        flash(f"Flujo '{nombre}' creado.", "success")
        return redirect(url_for("lista_flujos"))
    return render_template("nuevo_flujo.html", usuarios_empresa=usuarios_empresa)


@app.route("/flujos/<int:flujo_id>")
def ver_flujo(flujo_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    flujo = Flujo.query.get(flujo_id)
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    usuarios_empresa = Usuario.query.filter_by(empresa=empresa).all()
    return render_template("ver_flujo.html", flujo=flujo, usuarios_empresa=usuarios_empresa)


@app.route("/flujos/<int:flujo_id>/regla", methods=["POST"])
def nueva_regla(flujo_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    etapa_id    = request.form.get("etapa_id")
    trigger     = request.form.get("trigger","")
    accion      = request.form.get("accion","")
    destinatario= request.form.get("destinatario","responsable")
    mensaje     = request.form.get("mensaje","").strip()
    regla = FlujoRegla(
        flujo_id=flujo_id,
        etapa_id=int(etapa_id) if etapa_id else None,
        trigger=trigger, accion=accion,
        destinatario=destinatario, mensaje=mensaje
    )
    db.session.add(regla)
    db.session.commit()
    flash("Regla agregada.", "success")
    return redirect(url_for("ver_flujo", flujo_id=flujo_id))


@app.route("/flujos/<int:flujo_id>/toggle")
def toggle_flujo(flujo_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    flujo = Flujo.query.get(flujo_id)
    if flujo:
        flujo.activo = not flujo.activo
        db.session.commit()
        flash(f"Flujo {'activado' if flujo.activo else 'desactivado'}.", "success")
    return redirect(url_for("lista_flujos"))


def ejecutar_reglas(flujo_id, etapa_id, trigger, oportunidad=None, tarea=None):
    reglas = FlujoRegla.query.filter_by(
        flujo_id=flujo_id, etapa_id=etapa_id,
        trigger=trigger, activo=True
    ).all()
    for regla in reglas:
        try:
            destinatario_email = None
            if regla.destinatario == "responsable" and oportunidad and oportunidad.responsable_id:
                u = Usuario.query.get(oportunidad.responsable_id)
                if u: destinatario_email = u.correo
            elif regla.destinatario == "admin":
                etapa = FlujoEtapa.query.get(etapa_id)
                if etapa and etapa.responsable_id:
                    u = Usuario.query.get(etapa.responsable_id)
                    if u: destinatario_email = u.correo
            elif regla.destinatario == "tarea_asignado" and tarea and tarea.asignado_a:
                u = Usuario.query.get(tarea.asignado_a)
                if u: destinatario_email = u.correo

            if destinatario_email and regla.accion == "enviar_email":
                titulo = oportunidad.titulo if oportunidad else (tarea.descripcion if tarea else "")
                etapa_obj = FlujoEtapa.query.get(etapa_id)
                etapa_nombre = etapa_obj.nombre if etapa_obj else ""
                msg = Message(
                    subject=f"aruna — {regla.mensaje or 'Notificacion de flujo'}",
                    sender=app.config["MAIL_USERNAME"],
                    recipients=[destinatario_email]
                )
                msg.body = (
                    f"{regla.mensaje or 'Tienes una actualizacion en aruna.'}\n\n"
                    f"Elemento: {titulo}\n"
                    f"Etapa: {etapa_nombre}\n\n"
                    f"Ingresa a aruna para ver los detalles."
                )
                mail.send(msg)
        except Exception as e:
            print(f"Error ejecutando regla {regla.id}: {e}")


# -----------------------------
# Flujos / Workflow Engine
# -----------------------------



# -----------------------------
# API para n8n
# -----------------------------
@app.route("/api/suscripciones/por-vencer")
def api_suscripciones_por_vencer():
    api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
    if api_key != os.environ.get("N8N_API_KEY", "aruna-n8n-2024"):
        return jsonify({"error": "No autorizado"}), 401
    import datetime as dt
    today = dt.date.today()
    dias = int(request.args.get("dias", 7))
    fecha_limite = today + dt.timedelta(days=dias)
    suscripciones = Suscripcion.query.filter(
        Suscripcion.estado == "activa",
        Suscripcion.proximo_cobro <= fecha_limite,
        Suscripcion.proximo_cobro >= today
    ).all()
    resultado = []
    for s in suscripciones:
        dias_restantes = (s.proximo_cobro - today).days
        resultado.append({
            "id": s.id,
            "cliente": s.cliente_nombre,
            "plan": s.plan or "",
            "monto": float(s.monto),
            "frecuencia": s.frecuencia,
            "proximo_cobro": s.proximo_cobro.isoformat(),
            "dias_restantes": dias_restantes,
            "empresa": s.empresa,
            "correo_cliente": Cliente.query.get(s.cliente_id).correo if s.cliente_id else ""
        })
    return jsonify({
        "total": len(resultado),
        "fecha_consulta": today.isoformat(),
        "suscripciones": resultado
    })

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
