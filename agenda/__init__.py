from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, flash, redirect, request, url_for
from sqlalchemy import inspect, text

from config import Config
from .extensions import csrf, db, login_manager


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Entre na sua conta para acessar essa página."
    login_manager.login_message_category = "info"

    from . import models  # noqa: F401
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    @app.template_filter("month_short_pt")
    def month_short_pt(value):
        months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
        return months[value.month - 1]

    @app.context_processor
    def inject_globals():
        from datetime import date
        today = date.today()
        from flask_login import current_user
        from .models import Notification
        unread_count = Notification.query.filter_by(user_id=current_user.id, read_at=None).count() if current_user.is_authenticated else 0
        latest_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(3).all() if current_user.is_authenticated else []
        months = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        weekdays = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
        return {
            "current_year": today.year,
            "today_number": today.day,
            "today_month": months[today.month - 1],
            "today_month_short": months[today.month - 1][:3].upper(),
            "today_label": f"{weekdays[today.weekday()]}, {today.day} de {months[today.month - 1]} de {today.year}",
            "today_iso": today.isoformat(),
            "class_options": ["1° ADM", "2° ADM", "3° ADM", "1° INFO", "2° INFO", "3° INFO", "1° Módulo", "2° Módulo", "3° Módulo"],
            "unread_notifications_count": unread_count,
            "latest_notifications": latest_notifications,
        }

    with app.app_context():
        db.create_all()
        # db.create_all() does not add columns to an existing database.
        # Keep older local copies compatible when the profile-photo feature is introduced.
        user_columns = {column["name"] for column in inspect(db.engine).get_columns("users")}
        binary_type = "BYTEA" if db.engine.dialect.name == "postgresql" else "BLOB"
        additions = {
            "profile_photo": binary_type,
            "profile_photo_mimetype": "VARCHAR(80)",
            "matricula": "VARCHAR(10)",
        }
        missing = [(name, sql_type) for name, sql_type in additions.items() if name not in user_columns]
        if missing:
            with db.engine.begin() as connection:
                for name, sql_type in missing:
                    connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {sql_type}"))
        verification_columns = {column["name"] for column in inspect(db.engine).get_columns("email_verifications")}
        if "matricula" not in verification_columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE email_verifications ADD COLUMN matricula VARCHAR(10)"))
        with db.engine.begin() as connection:
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_matricula_unique ON users (matricula)"))
            connection.execute(text("UPDATE users SET class_name = '3° INFO' WHERE class_name = '3º ano (exemplo)'"))
            connection.execute(text("UPDATE schedule_items SET class_name = '3° INFO' WHERE class_name = '3º ano (exemplo)'"))
            connection.execute(text("UPDATE users SET matricula = '2024309536' WHERE email = 'aluno@agendaifal.local' AND matricula IS NULL AND NOT EXISTS (SELECT 1 FROM users WHERE matricula = '2024309536')"))
        from .seed import seed_demo_data
        seed_demo_data()

    @app.errorhandler(413)
    def uploaded_file_too_large(_error):
        flash("O envio ultrapassou o limite permitido para esta solicitação. Reduza o tamanho dos arquivos e tente novamente.", "error")
        referrer = request.referrer
        if referrer and urlparse(referrer).netloc == request.host:
            return redirect(referrer)
        return redirect(url_for("main.dashboard"))

    return app
