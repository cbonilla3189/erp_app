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
    empresa_admin = db.Column(db.Boolean, default=False)
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
    inventario_id = db.Column(db.Integer, db.ForeignKey("inventarios.id"))




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

class CampoPersonalizado(db.Model):
    __tablename__ = "campos_personalizados"
    id         = db.Column(db.Integer, primary_key=True)
    empresa    = db.Column(db.String(200), nullable=False)
    nombre     = db.Column(db.String(100), nullable=False)
    tipo       = db.Column(db.String(20), nullable=False)
    opciones   = db.Column(db.Text)
    creado_en     = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    inventario_id = db.Column(db.Integer, db.ForeignKey("inventarios.id"))
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
            stock_minimo = int(request.form.get("stock_minimo", 5))
            p = Producto(user_id=session["user_id"], nombre=nombre,
                         categoria=categoria, cantidad=cantidad, precio=precio,
                         stock_minimo=stock_minimo, inventario_id=inv_actual.id)
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
    valores = {}
    for v in ValorCampo.query.all():
        valores.setdefault(v.producto_id, {})[v.campo_id] = v.valor
    return render_template("inventario.html", productos=productos, campos=campos,
                           valores=valores, inv_actual=inv_actual, inventarios=inventarios)


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
            campo = CampoPersonalizado(empresa=empresa, nombre=nombre, tipo=tipo, opciones=opciones)
            db.session.add(campo)
            db.session.commit()
            flash(f"Campo '{nombre}' creado.", "success")
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
        cat = p.categoria or "Sin categoría"
        cats[cat] = cats.get(cat, 0) + 1
    user = Usuario.query.get(session["user_id"])
    empresa = user.empresa or ""
    campos = CampoPersonalizado.query.filter_by(empresa=empresa).all()
    return render_template("reportes.html",
        total=total,
        valor_total=valor_total,
        sin_stock=sin_stock,
        bajo_stock=bajo_stock,
        categorias=cats,
        productos=productos,
        alertas=alertas,
        campos=campos)


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
        nombre      = request.form.get("nombre", "").strip().title()
        descripcion = request.form.get("descripcion", "").strip()
        color       = request.form.get("color", "#561d9c")
        inv = Inventario(
            empresa=user.empresa or "",
            nombre=nombre,
            descripcion=descripcion,
            color=color,
            creado_por=user.id
        )
        db.session.add(inv)
        db.session.commit()
        flash(f"Inventario '{nombre}' creado.", "success")
        return redirect(url_for("lista_inventarios"))
    return render_template("nuevo_inventario.html")


@app.route("/inventarios/<int:inv_id>/eliminar", methods=["POST"])
def eliminar_inventario(inv_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    inv = Inventario.query.get(inv_id)
    if inv and inv.productos:
        flash("No puedes eliminar un inventario con productos.", "warning")
        return redirect(url_for("lista_inventarios"))
    if inv:
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

# -----------------------------
# Run
# -----------------------------

@app.route("/verificar/<int:user_id>", methods=["GET", "POST"])
def verify_code(user_id):
    user = Usuario.query.get(user_id)
    if not user:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("login"))
    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip()
        tv = TokenVerificacion.query.filter_by(user_id=user_id, token=codigo).first()
        if not tv:
            flash("Código incorrecto. Intenta de nuevo.", "danger")
            return render_template("verify.html", user_id=user_id, correo=user.correo)
        if datetime.datetime.now() > tv.fecha_expiracion:
            db.session.delete(tv)
            db.session.commit()
            flash("El código expiró. Regístrate de nuevo.", "warning")
            return redirect(url_for("register"))
        user.verificado = 1
        db.session.delete(tv)
        db.session.commit()
        return render_template("verify.html", mensaje="Cuenta verificada. Ya puedes iniciar sesión.")
    return render_template("verify.html", user_id=user_id, correo=user.correo)

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=False)
