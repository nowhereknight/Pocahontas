import io
import base64

from app import app, db, logging
from app.models import User, Enterprise, Value
from app.forms import LoginForm, RegistrationForm, EditProfileForm, EnterpriseForm
from flask import render_template, flash, redirect, request, url_for
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from datetime import datetime
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import json
import plotly
import plotly.express as px


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    form = EnterpriseForm()
    if form.validate_on_submit():
        enterprise = Enterprise(
            name=form.name.data, description=form.description.data, symbol=form.symbol.data, author=current_user
        )
        for value_name in form.values.data:
            value = Value.query.filter_by(name=value_name).first()
            if not value:
                value=Value(name=value_name)
            enterprise.values.append(value)
        db.session.add(enterprise)
        db.session.commit()

        flash("Tu empresa ha sido creada con éxito")
        return redirect(url_for("index"))

    page = request.args.get("page", 1, type=int)
    enterprises = current_user.get_all_enterprises().paginate(page, app.config["ENTERPRISES_PER_PAGE"], False)
    next_url = url_for("index", page=enterprises.next_num) if enterprises.has_next else None
    prev_url = url_for("index", page=enterprises.prev_num) if enterprises.has_prev else None
    return render_template(
        "index.html",
        title="Home",
        form=form,
        enterprises=enterprises.items,
        next_url=next_url,
        prev_url=prev_url,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Usuario y/o contraseña invàlidos")
            return redirect(url_for("login"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("index")
        return redirect(next_page)
    return render_template("login.html", title="Ingresar", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Felicidades. Ya has sido registrado")
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)


@app.route("/user/<username>")
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template("user.html", user=user)


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    """[summary]

    :return: [description]
    :rtype: [type]
    """
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Tus cambios han sido guardados")
        return redirect(url_for("edit_profile"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", title="Edit Profile", form=form)


@app.route('/render_graph')
@login_required
def render_graph():
    # Fixing random state for reproducibility
    np.random.seed(19680801)


    plt.rcdefaults()
    fig, ax = plt.subplots()

    # Example data
    enterprises = Enterprise.query.all()
    app.logger.error(enterprises)
    values_dict = {}
    for enterprise in enterprises:
        for value in enterprise.values:
            if value.name in values_dict:
                values_dict[value.name]+=1
            else:
                values_dict[value.name]=1
    values_list=[]
    count_list=[]
    for key in values_dict:
        values_list.append(key)
        count_list.append(values_dict[key])
    y_pos = np.arange(len(values_list))

    ax.barh(y_pos, count_list, align='center')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(values_list)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Incidencias')
    ax.set_title('Valores repetidos')
    
    # Convert plot to PNG image
    pngImage = io.BytesIO()
    FigureCanvas(fig).print_png(pngImage)
    
    # Encode PNG image to base64 string
    pngImageB64String = "data:image/png;base64,"
    pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')
    
    return render_template("chart.html", image=pngImageB64String)

