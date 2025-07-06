import os, json
from collections import defaultdict
from datetime import datetime

from flask import Flask, render_template, send_file, url_for, redirect, send_from_directory, request
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


app = Flask(__name__)
app.config.from_file("config.json", load=json.load)
db = SQLAlchemy(app, model_class=Base)
bcrypt = Bcrypt(app)


def split_reference(full_ref: str) -> tuple[int, str]:
    i = 0
    while i < len(full_ref) and full_ref[i].isdigit():
        i += 1
    return int(full_ref[:i]),full_ref[i:]


##==============================================
##                  LOGIN
##==============================================
login_manager = LoginManager(app)
login_manager.login_view = "login" # route to login page


Permissions = [
    {"id": 0, "name": "READ"},
    {"id": 1, "name": "READ-WRITE"},
]


class User(db.Model, UserMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)
    permission: Mapped[int] = mapped_column(nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = db.session.scalars(
            db.select(User).where(User.username == request.form["username"])
        ).first()
        if user:
            if bcrypt.check_password_hash(user.password, request.form["password"]):
                login_user(user)
                return redirect("/")
    return render_template("login.html")


@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


##==============================================
##               CAP DATABASE
##==============================================

Colors = [
    {"name": "Polychrome"},
    {"name": "Blanc"},
    {"name": "Crème"},
    {"name": "Or"},
    {"name": "Rose"},
    {"name": "Rouge"},
    {"name": "Bordeau"},
    {"name": "Violet"},
    {"name": "Vert"},
    {"name": "Bleu"},
    {"name": "Marron"},
    {"name": "Gris"},
    {"name": "Noir"},
    {"name": "Jaune"},
    {"name": "Orange"},
]


Diameters = [
    {"name": "Huitième (24mm)"},
    {"name": "Quart (26mm)"},
    {"name": "Cuvée spéciale (28mm)"},
    {"name": "Default (30mm)"},
    {"name": "Jéroboam (33mm)"},
    {"name": "Nabuchodonosor (40mm)"},
]


class Capsule(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(nullable=False)
    reference: Mapped[int]
    sub_reference: Mapped[str]
    brand: Mapped[int]
    date_created: Mapped[str] = mapped_column(nullable=False, default=datetime.now().strftime("%d-%m-%y"))
    text_top: Mapped[str]
    text_aside: Mapped[str]
    background_color: Mapped[int]
    aside_color: Mapped[int]
    text_color: Mapped[int]
    text_aside_color: Mapped[int]
    diameter: Mapped[int]


class Brand(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str]


##==============================================
##               NON ADMIN ROUTES
##==============================================


@app.route("/images/<int:id>")
def images(id):
    filename = f"{id // 100}/{id}.jpg"
    if os.path.isfile(f"{app.config['CAP_IMAGES']}/{filename}"):
        return send_from_directory(
            app.config["CAP_IMAGES"], filename, as_attachment=False
        )
    else:
        return send_file("static/images/default.jpg")


@app.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    brand_name = request.args.get("brand_name", None, type=str)
    reference = request.args.get("reference", None, type=str)
    text_top = request.args.get("text_top", None, type=str)
    text_aside = request.args.get("text_aside", None, type=str)
    background_color = request.args.get("background_color", None, type=int)
    aside_color = request.args.get("aside_color", None, type=int)
    text_color = request.args.get("text_color", None, type=int)
    text_aside_color = request.args.get("text_aside_color", None, type=int)
    diameter = request.args.get("diameter", None, type=int)
    brand = None

    query = Capsule.query.join(Brand, Brand.id == Capsule.brand)
    if brand_name:
        brand = Brand.query.filter(Brand.name.like(brand_name)).first()
        if brand:
            query = query.filter(Capsule.brand == brand.id)
    if reference:
        ref, sub_ref = split_reference(reference)
        query = query.filter(Capsule.reference == ref, Capsule.sub_reference == sub_ref)
    if text_top:
        query = query.filter(Capsule.text_top.ilike(f"%{text_top}%"))
    if text_aside:
        query = query.filter(Capsule.text_aside.ilike(f"%{text_aside}%"))
    if background_color is not None:
        query = query.filter(Capsule.background_color == background_color)
    if aside_color is not None:
        query = query.filter(Capsule.aside_color == aside_color)
    if text_color is not None:
        query = query.filter(Capsule.text_color == text_color)
    if text_aside_color is not None:
        query = query.filter(Capsule.text_aside_color == text_aside_color)
    if diameter is not None:
        query = query.filter(Capsule.diameter == diameter)

    query = query.order_by(Brand.name, Capsule.reference, Capsule.sub_reference)
    caps = query.paginate(page=page, per_page=48)

    args = request.args.copy()
    args["page"] = page - 1
    url_prev = url_for('index', **args)
    args["page"] = page + 1
    url_next = url_for('index', **args)

    return render_template("caps.html", caps=caps, url_prev=url_prev, url_next=url_next, brand=brand)


@app.route("/info/<int:id>")
def info(id):
    cap = Capsule.query.get_or_404(id)
    brand = Brand.query.get_or_404(cap.brand)
    cap.reference = f"{cap.reference}{cap.sub_reference}"
    return render_template("info.html", cap=cap, brand=brand, colors=Colors, diameters=Diameters)


@app.route("/search", methods=["POST", "GET"])
def search():
    if request.method == "GET":
        return render_template("search.html", colors=Colors, diameters=Diameters)
    else:
        return redirect(url_for('index', **request.form))


@app.route("/brand", methods=["GET"])
def brand():
    brands = Brand.query.order_by(Brand.name).all()
    data = defaultdict(list)
    for brand in brands:
        data[brand.name[0]].append(brand)
    return render_template("brand.html", data=data)


##==============================================
##               ADMIN ROUTES
##==============================================

@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    cap_id = request.args.get("id", None, type=int)

    if request.method == "GET":
        if cap_id is None:
            return render_template("edit.html", colors=Colors, diameters=Diameters, values={})
        else:
            cap = Capsule.query.get_or_404(cap_id)
            brand = Brand.query.get_or_404(cap.brand).name
            values = cap.__dict__
            values["brand_name"] = brand
            values["reference"] = f"{cap.reference}{cap.sub_reference}"
            return render_template("edit.html", colors=Colors, diameters=Diameters, values=values)

    elif request.form["type"] == "delete_capsule":
        cap = Capsule.query.get_or_404(cap_id)
        db.session.delete(cap)
        db.session.commit()

    elif request.form["type"] in ["update_capsule", "create_capsule"]:
        brand = Brand.query.filter_by(name=request.form["brand_name"]).first_or_404("brand not found")
        if request.form["type"] == "update_capsule":
            cap = Capsule.query.get_or_404(cap_id)
        else:
            cap = Capsule()
            db.session.add(cap)
        cap.title = request.form["title"]
        cap.reference, cap.sub_reference = split_reference(request.form["reference"])
        cap.brand = brand.id
        cap.text_top = request.form["text_top"]
        cap.text_aside = request.form["text_aside"]
        cap.background_color = request.form["background_color"]
        cap.aside_color = request.form["aside_color"]
        cap.text_aside_color = request.form["text_aside_color"]
        cap.text_color = request.form["text_color"]
        cap.diameter = request.form["diameter"]
        db.session.commit()

        return redirect(url_for("info", id=cap.id))

    elif request.form["type"] == "create_brand":
        brand = Brand(
            name = request.form["name"].strip(),
            description =  request.form["description"]
        )
        db.session.add(brand)
        db.session.commit()

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host='0.0.0.0')
