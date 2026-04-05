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
    verificado  = db.Column(db.Integer, default=0)
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
@app.context_processor
def inject_user():
    return {"usuario": session.get("username")}


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
        nombre    = request.form.get("nombre", "").strip()
        apellido  = request.form.get("apellido", "").strip()
        empresa   = request.form.get("empresa", "").strip()
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

        user = Usuario(
            nombre=nombre, apellido=apellido, empresa=empresa,
            correo=correo, ruc=ruc, dv=dv, telefono=telefono,
            username=username, password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        token = secrets.token_urlsafe(20)
        expiracion = datetime.datetime.now() + datetime.timedelta(minutes=30)
        tv = TokenVerificacion(user_id=user.id, token=token, fecha_expiracion=expiracion)
        db.session.add(tv)
        db.session.commit()

        try:
            msg = Message("Verifica tu cuenta - Aruna ERP",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[correo])
            link = url_for("verify", token=token, _external=True)
            msg.body = (f"Hola {nombre},\n\nVerifica tu cuenta:\n\n{link}\n\n"
                        "Expira en 30 minutos.")
            mail.send(msg)
        except Exception as e:
            print("Error enviando correo:", e)
            flash("Registro creado, pero no fue posible enviar el correo.", "warning")

        flash("Registro exitoso. Revisa tu correo.", "success")
        return redirect(url_for("login"))
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
        user.nombre   = request.form.get("nombre", user.nombre)
        user.apellido = request.form.get("apellido", user.apellido)
        user.empresa  = request.form.get("empresa", user.empresa)
        user.correo   = request.form.get("correo", user.correo)
        user.telefono = request.form.get("telefono", user.telefono)
        db.session.commit()
        flash("Usuario actualizado.", "success")
        return redirect(url_for("admin_panel"))
    return render_template("editar_usuario.html", usuario=user)


# -----------------------------
# Dashboard
# -----------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    total = Producto.query.filter_by(user_id=session["user_id"]).count()
    ultimos = Producto.query.filter_by(
        user_id=session["user_id"]).order_by(
        Producto.creado_en.desc()).limit(5).all()
    return render_template("dashboard.html",
                           usuario=session.get("username"),
                           total_productos=total, ultimos=ultimos)


# -----------------------------
# Inventario
# -----------------------------
@app.route("/inventario", methods=["GET", "POST"])
def inventario():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        nombre    = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "").strip()
        cantidad  = int(request.form.get("cantidad", 0))
        precio    = float(request.form.get("precio") or 0)
        if not nombre:
            flash("Debe ingresar un nombre.", "warning")
        else:
            p = Producto(user_id=session["user_id"], nombre=nombre,
                         categoria=categoria, cantidad=cantidad, precio=precio)
            db.session.add(p)
            db.session.commit()
            flash("Producto agregado.", "success")
    productos = Producto.query.filter_by(
        user_id=session["user_id"]).order_by(Producto.creado_en.desc()).all()
    return render_template("inventario.html", productos=productos)


@app.route("/inventario/editar/<int:producto_id>", methods=["GET", "POST"])
def inventario_editar(producto_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    prod = Producto.query.filter_by(
        id=producto_id, user_id=session["user_id"]).first()
    if not prod:
        flash("Producto no encontrado.", "danger")
        return redirect(url_for("inventario"))
    if request.method == "POST":
        prod.nombre    = request.form.get("nombre", prod.nombre)
        prod.categoria = request.form.get("categoria", prod.categoria)
        prod.cantidad  = int(request.form.get("cantidad", prod.cantidad))
        prod.precio    = float(request.form.get("precio", prod.precio))
        db.session.commit()
        flash("Producto actualizado.", "success")
        return redirect(url_for("inventario"))
    return render_template("inventario_editar.html", producto=prod)


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
    return render_template("mi_empresa.html", empresa=user.empresa, usuario=user)


@app.route("/usuarios_empresa")
def usuarios_empresa():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = Usuario.query.get(session["user_id"])
    usuarios = Usuario.query.filter_by(empresa=user.empresa).all()
    return render_template("usuarios_empresa.html", usuarios=usuarios)


# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=False)
