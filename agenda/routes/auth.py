from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func

from ..extensions import db
from ..models import User
from ..utils import clean_text


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = clean_text(request.form.get("email")).lower()
        password = request.form.get("password", "")
        user = db.session.query(User).filter(func.lower(User.email) == email).first()

        if user and user.check_password(password):
            login_user(user, remember=bool(request.form.get("remember")))
            flash(f"Olá, {user.name.split()[0]}! Seja bem-vindo(a).", "success")
            return redirect(url_for("main.dashboard"))

        flash("E-mail ou senha incorretos.", "error")

    return render_template("auth/login.html")


@auth_bp.post("/logout")
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))
