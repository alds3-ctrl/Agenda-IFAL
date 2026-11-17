from datetime import date
import io

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from ..models import Event, Notice, ScheduleItem, User


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
@login_required
def dashboard():
    today = date.today()
    upcoming_events = Event.query.filter(Event.event_date >= today).order_by(Event.event_date.asc()).limit(5).all()
    recent_notices = Notice.query.order_by(Notice.is_pinned.desc(), Notice.published_at.desc(), Notice.created_at.desc()).limit(4).all()
    activities_query = ScheduleItem.query.filter(ScheduleItem.due_date >= today)
    if not current_user.is_admin:
        if current_user.class_name:
            activities_query = activities_query.filter(ScheduleItem.class_name == current_user.class_name)
        else:
            activities_query = activities_query.filter(ScheduleItem.id == -1)
    activities_count = activities_query.count()
    next_activities = activities_query.order_by(ScheduleItem.due_date.asc()).limit(5).all()

    return render_template(
        "dashboard.html",
        upcoming_events=upcoming_events,
        recent_notices=recent_notices,
        next_activities=next_activities,
        events_count=Event.query.filter(Event.event_date >= today).count(),
        notices_count=Notice.query.count(),
        activities_count=activities_count,
    )


@main_bp.get("/agenda")
@login_required
def agenda():
    query = (request.args.get("q") or "").strip()
    category = (request.args.get("categoria") or "").strip()
    events_query = Event.query
    if query:
        like = f"%{query}%"
        events_query = events_query.filter((Event.title.ilike(like)) | (Event.description.ilike(like)) | (Event.location.ilike(like)))
    if category:
        events_query = events_query.filter(Event.category == category)
    events = events_query.order_by(Event.event_date.asc(), Event.start_time.asc()).all()
    categories = [row[0] for row in Event.query.with_entities(Event.category).distinct().order_by(Event.category).all()]
    return render_template("agenda.html", events=events, categories=categories, query=query, selected_category=category)


@main_bp.get("/cronogramas")
@login_required
def schedules():
    selected_class = (request.args.get("turma") or "").strip()
    selected_term = (request.args.get("bimestre") or "").strip()
    items_query = ScheduleItem.query

    if not current_user.is_admin:
        if current_user.class_name:
            selected_class = current_user.class_name
            items_query = items_query.filter(ScheduleItem.class_name == current_user.class_name)
        else:
            items_query = items_query.filter(ScheduleItem.id == -1)
    elif selected_class:
        items_query = items_query.filter(ScheduleItem.class_name == selected_class)

    if selected_term:
        items_query = items_query.filter(ScheduleItem.term == selected_term)

    items = items_query.order_by(ScheduleItem.due_date.asc()).all()
    classes = [row[0] for row in ScheduleItem.query.with_entities(ScheduleItem.class_name).distinct().order_by(ScheduleItem.class_name).all()]
    terms = ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"]
    return render_template(
        "schedules.html",
        items=items,
        classes=classes,
        terms=terms,
        selected_class=selected_class,
        selected_term=selected_term,
    )


@main_bp.get("/avisos")
@login_required
def notices():
    items = Notice.query.order_by(Notice.is_pinned.desc(), Notice.published_at.desc(), Notice.created_at.desc()).all()
    return render_template("notices.html", notices=items)


@main_bp.get("/minha-conta")
@login_required
def account():
    return render_template("account.html")


@main_bp.get("/usuarios/<int:user_id>/foto")
@login_required
def profile_photo(user_id):
    user = User.query.get_or_404(user_id)
    if not user.profile_photo:
        abort(404)
    response = send_file(
        io.BytesIO(user.profile_photo),
        mimetype=user.profile_photo_mimetype or "image/webp",
        download_name=f"perfil-{user.id}.webp",
        max_age=0,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@main_bp.post("/minha-conta")
@login_required
def update_account():
    from PIL import Image, ImageOps, UnidentifiedImageError

    from ..extensions import db
    from ..utils import clean_text

    name = clean_text(request.form.get("name"))
    new_password = request.form.get("new_password", "")
    current_password = request.form.get("current_password", "")
    uploaded = request.files.get("profile_photo")
    remove_photo = request.form.get("remove_photo") == "1"

    if not name:
        flash("Informe seu nome.", "error")
        return redirect(url_for("main.account"))
    if new_password and not current_user.check_password(current_password):
        flash("A senha atual não confere. A senha não foi alterada.", "error")
        return redirect(url_for("main.account"))
    if new_password and len(new_password) < 8:
        flash("A nova senha deve ter pelo menos 8 caracteres.", "error")
        return redirect(url_for("main.account"))

    photo_bytes = None
    photo_mimetype = None
    if uploaded and uploaded.filename:
        raw = uploaded.read(3 * 1024 * 1024 + 1)
        if len(raw) > 3 * 1024 * 1024:
            flash("A foto deve ter no máximo 3 MB.", "error")
            return redirect(url_for("main.account"))
        try:
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Use uma imagem JPG, PNG ou WEBP.")
                if source.width * source.height > 12_000_000:
                    raise ValueError("A imagem possui resolução muito alta. Escolha outra foto.")
                source.load()
                source = ImageOps.exif_transpose(source)
                has_alpha = "A" in source.getbands() or "transparency" in source.info
                source.thumbnail((512, 512), Image.Resampling.LANCZOS)
                source = source.convert("RGBA" if has_alpha else "RGB")
                output = io.BytesIO()
                source.save(output, format="WEBP", quality=88, method=6)
                photo_bytes = output.getvalue()
                photo_mimetype = "image/webp"
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
            message = str(error) if isinstance(error, ValueError) else "Não foi possível ler essa imagem. Tente outro arquivo."
            flash(message, "error")
            return redirect(url_for("main.account"))

    current_user.name = name
    if new_password:
        current_user.set_password(new_password)
    if photo_bytes is not None:
        current_user.profile_photo = photo_bytes
        current_user.profile_photo_mimetype = photo_mimetype
    elif remove_photo:
        current_user.profile_photo = None
        current_user.profile_photo_mimetype = None

    db.session.commit()
    flash("Seus dados foram atualizados.", "success")
    return redirect(url_for("main.account"))
