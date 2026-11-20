from datetime import date, datetime, timedelta
import calendar as pycalendar
import hashlib, hmac, io, secrets, re

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from ..extensions import db

from ..models import (AcademicPeriod, AcademicRequest, Attachment, EmailChangeVerification, Event, Favorite, Material, Notification, Notice, PersonalTask, ScheduleItem, TimetableEntry, User)
from ..utils import CLASS_OPTIONS, valid_password


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
@login_required
def dashboard():
    today = date.today()
    _create_due_reminders(current_user, today)
    upcoming_events = Event.query.filter(Event.event_date >= today).order_by(Event.event_date.asc()).limit(5).all()
    recent_notices = Notice.query.filter(Notice.published_at <= today).order_by(Notice.is_pinned.desc(), Notice.published_at.desc(), Notice.created_at.desc()).limit(4).all()
    activities_query = ScheduleItem.query.filter(ScheduleItem.due_date >= today)
    if not current_user.is_admin:
        if current_user.class_name:
            activities_query = activities_query.filter(ScheduleItem.class_name == current_user.class_name)
        else:
            activities_query = activities_query.filter(ScheduleItem.id == -1)
    activities_count = activities_query.count()
    next_activities = activities_query.order_by(ScheduleItem.due_date.asc()).limit(5).all()

    countdown_items = [(event.title, event.event_date, (event.event_date - today).days, "Evento") for event in Event.query.filter(Event.event_date >= today).order_by(Event.event_date.asc()).limit(6).all()]
    countdown_query = ScheduleItem.query.filter(ScheduleItem.due_date >= today, ScheduleItem.due_date <= today + timedelta(days=14))
    if not current_user.is_admin: countdown_query = countdown_query.filter_by(class_name=current_user.class_name)
    countdown_items += [(item.title, item.due_date, (item.due_date - today).days, item.activity_type) for item in countdown_query.order_by(ScheduleItem.due_date.asc()).limit(6).all()]
    countdown_items = sorted(countdown_items, key=lambda item: item[1])[:6]
    personal_tasks = PersonalTask.query.filter_by(user_id=current_user.id, completed=False).order_by(PersonalTask.due_date.asc()).limit(4).all()
    unread_notifications = Notification.query.filter_by(user_id=current_user.id, read_at=None).order_by(Notification.created_at.desc()).limit(5).all()
    return render_template(
        "dashboard.html",
        upcoming_events=upcoming_events,
        recent_notices=recent_notices,
        next_activities=next_activities,
        events_count=Event.query.filter(Event.event_date >= today).count(),
        notices_count=Notice.query.filter(Notice.published_at <= today).count(),
        activities_count=activities_count,
        countdown_items=countdown_items, personal_tasks=personal_tasks, unread_notifications=unread_notifications,
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
    classes = CLASS_OPTIONS
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
    items = Notice.query.filter(Notice.published_at <= date.today()).order_by(Notice.is_pinned.desc(), Notice.published_at.desc(), Notice.created_at.desc()).all()
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


@main_bp.get("/anexos/<int:attachment_id>")
@login_required
def attachment_file(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    if not current_user.is_admin and attachment.schedule_item and attachment.schedule_item.class_name != current_user.class_name:
        abort(403)
    download = request.args.get("download") == "1"
    safe_inline_types = {"image/png", "image/jpeg", "image/webp", "application/pdf"}
    as_attachment = download or attachment.mimetype not in safe_inline_types
    response = send_file(
        io.BytesIO(attachment.data),
        mimetype=attachment.mimetype,
        as_attachment=as_attachment,
        download_name=attachment.original_filename,
        max_age=0,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-store"
    return response


@main_bp.post("/minha-conta")
@login_required
def update_account():
    from PIL import Image, ImageOps, UnidentifiedImageError
    from sqlalchemy import func
    from ..utils import clean_text, is_student_email, valid_matricula

    name = clean_text(request.form.get("name"))
    new_email = clean_text(request.form.get("email")).lower()
    new_matricula = clean_text(request.form.get("matricula"))
    new_class = clean_text(request.form.get("class_name"))
    new_password = request.form.get("new_password", "")
    current_password = request.form.get("current_password", "")
    uploaded = request.files.get("profile_photo")
    remove_photo = request.form.get("remove_photo") == "1"

    if not name or len(name) > 120:
        flash("Informe um nome válido.", "error")
        return redirect(url_for("main.account"))
    if new_password and not valid_password(new_password):
        flash("A nova senha precisa ter pelo menos 8 caracteres, um número e um caractere especial.", "error")
        return redirect(url_for("main.account"))
    if new_password and not current_password:
        try:
            from .auth import begin_password_reset
            begin_password_reset(current_user, pending_password=new_password)
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("main.account"))
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Falha ao enviar confirmação de senha pelo perfil")
            flash("Não foi possível enviar o código ao e-mail cadastrado.", "error")
            return redirect(url_for("main.account"))
        flash("Enviamos um código ao seu e-mail. Confirme-o para alterar a senha sem informar a senha atual.", "success")
        return redirect(url_for("auth.verify_password_reset", identifier=current_user.email, profile="1"))
    if not current_user.check_password(current_password):
        flash("A senha atual está incorreta. Para alterá-la sem lembrar a senha, deixe o campo vazio e confirme por e-mail.", "error")
        return redirect(url_for("main.account"))

    if not current_user.is_admin:
        if not is_student_email(new_email):
            flash("Estudantes devem utilizar um e-mail @aluno.ifal.edu.br.", "error")
            return redirect(url_for("main.account"))
        if not valid_matricula(new_matricula):
            flash("A matrícula deve conter exatamente 10 números.", "error")
            return redirect(url_for("main.account"))
        if new_class not in CLASS_OPTIONS:
            flash("Selecione uma das turmas disponíveis.", "error")
            return redirect(url_for("main.account"))
        existing = User.query.filter(User.matricula == new_matricula, User.id != current_user.id).first()
        if existing:
            flash("Esta matrícula já está vinculada a outra conta.", "error")
            return redirect(url_for("main.account"))
    elif not new_email or len(new_email) > 160 or "@" not in new_email:
        flash("Informe um e-mail válido.", "error")
        return redirect(url_for("main.account"))

    # Validate and normalize the photo before sending any email-verification code.
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
                    raise ValueError("A imagem possui resolução muito alta.")
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
            flash(str(error) if isinstance(error, ValueError) else "Não foi possível ler essa imagem.", "error")
            return redirect(url_for("main.account"))

    email_changed = new_email != current_user.email.lower()
    if email_changed:
        if User.query.filter(func.lower(User.email) == new_email).first():
            flash("Este e-mail já está sendo utilizado.", "error")
            return redirect(url_for("main.account"))
        pending = EmailChangeVerification.query.filter_by(user_id=current_user.id).first()
        other_pending = EmailChangeVerification.query.filter(
            func.lower(EmailChangeVerification.new_email) == new_email,
            EmailChangeVerification.user_id != current_user.id,
        ).first()
        if other_pending:
            flash("Este e-mail já está aguardando confirmação em outra conta.", "error")
            return redirect(url_for("main.account"))
        now = datetime.utcnow()
        if pending and now - pending.last_sent_at < timedelta(seconds=60):
            flash("Aguarde um minuto antes de solicitar outro código para o novo e-mail.", "error")
            return redirect(url_for("main.account"))
        code = f"{secrets.randbelow(1_000_000):06d}"
        try:
            from ..mailer import send_verification_code
            send_verification_code(new_email, code)
        except Exception:
            current_app.logger.exception("Falha ao enviar confirmação de alteração de e-mail")
            flash("Não foi possível enviar o código ao novo e-mail. Nenhuma alteração de e-mail foi feita.", "error")
            return redirect(url_for("main.account"))
        if not pending:
            pending = EmailChangeVerification(user_id=current_user.id, new_email=new_email)
            db.session.add(pending)
        pending.new_email = new_email
        pending.code_hash = hmac.new(str(current_app.secret_key).encode(), f"{new_email}:{code}".encode(), hashlib.sha256).hexdigest()
        pending.attempts = 0
        pending.expires_at = now + timedelta(minutes=10)
        pending.last_sent_at = now

    current_user.name = name
    if not current_user.is_admin:
        current_user.matricula = new_matricula
        current_user.class_name = new_class
    if new_password:
        current_user.set_password(new_password)
    if photo_bytes is not None:
        current_user.profile_photo = photo_bytes
        current_user.profile_photo_mimetype = photo_mimetype
    elif remove_photo:
        current_user.profile_photo = None
        current_user.profile_photo_mimetype = None

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Falha ao salvar alterações do perfil")
        flash("Não foi possível salvar as alterações. Confira os dados e tente novamente.", "error")
        return redirect(url_for("main.account"))

    if email_changed:
        flash("Enviamos um código para o novo e-mail. Confirme-o para concluir a alteração do endereço.", "success")
        return redirect(url_for("main.verify_email_change"))
    flash("Seus dados foram atualizados.", "success")
    return redirect(url_for("main.account"))


@main_bp.route("/minha-conta/verificar-email", methods=["GET", "POST"])
@login_required
def verify_email_change():
    from ..extensions import db
    pending = EmailChangeVerification.query.filter_by(user_id=current_user.id).first()
    if not pending:
        flash("Não existe alteração de e-mail aguardando confirmação.", "info"); return redirect(url_for("main.account"))
    if request.method == "POST":
        code = (request.form.get("code") or "").strip()
        expected = hmac.new(str(current_app.secret_key).encode(), f"{pending.new_email}:{code}".encode(), hashlib.sha256).hexdigest()
        if pending.expires_at < datetime.utcnow():
            flash("O código expirou. Solicite a alteração novamente.", "error")
        elif pending.attempts >= 5:
            flash("Limite de tentativas atingido. Solicite a alteração novamente.", "error")
        elif not re.fullmatch(r"\d{6}", code) or not hmac.compare_digest(expected, pending.code_hash):
            pending.attempts += 1; db.session.commit(); flash("Código incorreto.", "error")
        elif User.query.filter(User.email == pending.new_email, User.id != current_user.id).first():
            flash("Este e-mail já está sendo utilizado.", "error")
        else:
            current_user.email = pending.new_email
            db.session.delete(pending); db.session.commit()
            flash("E-mail atualizado e confirmado com sucesso.", "success")
            return redirect(url_for("main.account"))
    return render_template("verify_email_change.html", pending=pending)


def _create_due_reminders(user, today):
    from ..extensions import db
    if user.is_admin: return
    events = Event.query.filter(Event.event_date >= today, Event.event_date <= today + timedelta(days=7)).all()
    activities = ScheduleItem.query.filter(ScheduleItem.class_name == (user.class_name or ""), ScheduleItem.due_date >= today, ScheduleItem.due_date <= today + timedelta(days=7)).all()
    for event in events:
        fingerprint = f"event-pub:{event.id}:{user.id}"
        if not Notification.query.filter_by(fingerprint=fingerprint).first():
            db.session.add(Notification(user_id=user.id, title="Evento se aproximando", message=f"{event.title} acontece em {event.event_date.strftime('%d/%m/%Y')}.", link=url_for("main.agenda"), fingerprint=fingerprint))
    for item in activities:
        fingerprint = f"schedule-pub:{item.id}:{user.id}"
        if not Notification.query.filter_by(fingerprint=fingerprint).first():
            db.session.add(Notification(user_id=user.id, title="Prazo acadêmico próximo", message=f"{item.title} — entrega em {item.due_date.strftime('%d/%m/%Y')}.", link=url_for("main.schedules"), fingerprint=fingerprint))
    for task in PersonalTask.query.filter_by(user_id=user.id, completed=False).filter(PersonalTask.due_date >= today, PersonalTask.due_date <= today + timedelta(days=3)).all():
        fingerprint = f"personal-task:{user.id}:{task.id}"
        if not Notification.query.filter_by(fingerprint=fingerprint).first():
            db.session.add(Notification(user_id=user.id, title="Lembrete do seu planejamento", message=f"{task.title} vence em {task.due_date.strftime('%d/%m/%Y')}.", link=url_for("main.planning"), fingerprint=fingerprint))
    for notice in Notice.query.filter(Notice.published_at <= today, Notice.published_at >= today - timedelta(days=30)).all():
        fingerprint = f"notice:{notice.id}:{user.id}"
        if not Notification.query.filter_by(fingerprint=fingerprint).first():
            db.session.add(Notification(user_id=user.id, title="Novo aviso institucional", message=notice.title, link=url_for("main.notices"), fingerprint=fingerprint))
    db.session.commit()


@main_bp.get("/planejamento")
@login_required
def planning():
    tasks = PersonalTask.query.filter_by(user_id=current_user.id).order_by(PersonalTask.completed.asc(), PersonalTask.due_date.asc().nullslast(), PersonalTask.created_at.desc()).all()
    return render_template("planning.html", tasks=tasks)


@main_bp.post("/planejamento/novo")
@login_required
def add_task():
    from ..extensions import db
    from ..utils import parse_date, clean_text
    title = clean_text(request.form.get("title"))
    if not title or len(title) > 160:
        flash("Informe um título válido para a tarefa.", "error")
    else:
        due = clean_text(request.form.get("due_date"))
        try:
            due_date = parse_date(due, "prazo") if due else None
            task = PersonalTask(
                user_id=current_user.id,
                title=title,
                description=clean_text(request.form.get("description"))[:3000],
                due_date=due_date,
                priority=request.form.get("priority") if request.form.get("priority") in {"Baixa", "Média", "Alta"} else "Média",
            )
            db.session.add(task)
            db.session.commit()
            flash("Tarefa adicionada ao seu planejamento.", "success")
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
    return redirect(url_for("main.planning"))


@main_bp.post("/planejamento/<int:task_id>/editar")
@login_required
def edit_task(task_id):
    from ..utils import parse_date, clean_text
    task = PersonalTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    title = clean_text(request.form.get("title"))
    due = clean_text(request.form.get("due_date"))
    if not title or len(title) > 160:
        flash("Informe um título válido para a tarefa.", "error")
        return redirect(url_for("main.planning"))
    try:
        task.title = title
        task.description = clean_text(request.form.get("description"))[:3000]
        task.due_date = parse_date(due, "prazo") if due else None
        task.priority = request.form.get("priority") if request.form.get("priority") in {"Baixa", "Média", "Alta"} else "Média"
        db.session.commit()
        flash("Tarefa atualizada.", "success")
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "error")
    return redirect(url_for("main.planning"))


@main_bp.post("/planejamento/<int:task_id>/concluir")
@login_required
def toggle_task(task_id):
    from ..extensions import db
    task = PersonalTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404(); task.completed = not task.completed; db.session.commit()
    return redirect(url_for("main.planning"))


@main_bp.post("/planejamento/<int:task_id>/excluir")
@login_required
def delete_task(task_id):
    from ..extensions import db
    task = PersonalTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404(); db.session.delete(task); db.session.commit(); flash("Tarefa removida.", "success")
    return redirect(url_for("main.planning"))


@main_bp.get("/notificacoes")
@login_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return render_template("notifications.html", notifications=items)


@main_bp.get("/notificacoes/<int:notification_id>/abrir")
@login_required
def open_notification(notification_id):
    item = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    if item.read_at is None:
        item.read_at = datetime.utcnow()
        db.session.commit()
    return redirect(item.link or url_for("main.notifications"))


@main_bp.post("/notificacoes/<int:notification_id>/ler")
@login_required
def mark_notification_read(notification_id):
    from ..extensions import db
    item = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404(); item.read_at = datetime.utcnow(); db.session.commit()
    return redirect(item.link or url_for("main.notifications"))


@main_bp.post("/notificacoes/ler-todas")
@login_required
def mark_all_notifications_read():
    from ..extensions import db
    Notification.query.filter_by(user_id=current_user.id, read_at=None).update({"read_at": datetime.utcnow()}); db.session.commit(); flash("Notificações marcadas como lidas.", "success")
    return redirect(url_for("main.notifications"))


@main_bp.get("/calendario")
@login_required
def calendar():
    year = request.args.get("ano", type=int) or date.today().year; month = request.args.get("mes", type=int) or date.today().month
    if month < 1 or month > 12: month = date.today().month
    start = date(year, month, 1); end = date(year + (month == 12), 1 if month == 12 else month + 1, 1) - timedelta(days=1)
    events = Event.query.filter(Event.event_date >= start, Event.event_date <= end).order_by(Event.event_date).all()
    periods = AcademicPeriod.query.filter(AcademicPeriod.start_date <= end, AcademicPeriod.end_date >= start).all()
    activities_query = ScheduleItem.query.filter(ScheduleItem.due_date >= start, ScheduleItem.due_date <= end)
    if not current_user.is_admin: activities_query = activities_query.filter_by(class_name=current_user.class_name)
    calendar_activities = activities_query.order_by(ScheduleItem.due_date).all()
    return render_template("calendar.html", events=events, periods=periods, calendar_activities=calendar_activities, year=year, month=month, month_start=start, month_end=end, month_weeks=pycalendar.monthcalendar(year, month), month_label=["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"][month-1], prev_month=(date(year-1,12,1) if month==1 else date(year,month-1,1)), next_month=(date(year+1,1,1) if month==12 else date(year,month+1,1)))


@main_bp.get("/horario")
@login_required
def timetable():
    class_name = current_user.class_name if not current_user.is_admin else (request.args.get("turma") or "")
    entries = TimetableEntry.query.filter_by(class_name=class_name).order_by(TimetableEntry.weekday, TimetableEntry.start_time).all() if class_name else []
    return render_template("timetable.html", entries=entries, selected_class=class_name)


@main_bp.get("/materiais")
@login_required
def materials():
    query = (request.args.get("q") or "").strip()
    items_query = Material.query
    if not current_user.is_admin: items_query = items_query.filter((Material.class_name == None) | (Material.class_name == current_user.class_name))
    if query:
        like = f"%{query}%"; items_query = items_query.filter((Material.title.ilike(like)) | (Material.subject.ilike(like)) | (Material.description.ilike(like)))
    return render_template("materials.html", materials=items_query.order_by(Material.created_at.desc()).all(), query=query)


@main_bp.get("/materiais/<int:material_id>/download")
@login_required
def download_material(material_id):
    material = Material.query.get_or_404(material_id)
    if not current_user.is_admin and material.class_name and material.class_name != current_user.class_name: abort(403)
    response = send_file(io.BytesIO(material.data), mimetype=material.mimetype, as_attachment=True, download_name=material.filename)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-store"
    return response


@main_bp.get("/favoritos")
@login_required
def favorites():
    saved = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all()
    results = []
    models = {"event": Event, "notice": Notice, "schedule": ScheduleItem, "material": Material}
    today = date.today()
    for favorite in saved:
        model = models.get(favorite.entity_type)
        obj = db.session.get(model, favorite.entity_id) if model else None
        if obj is None:
            continue
        if favorite.entity_type == "notice" and obj.published_at > today:
            continue
        if favorite.entity_type == "schedule" and not current_user.is_admin and obj.class_name != current_user.class_name:
            continue
        if favorite.entity_type == "material" and not current_user.is_admin and obj.class_name and obj.class_name != current_user.class_name:
            continue
        results.append((favorite, obj))
    return render_template("favorites.html", favorites=results)


@main_bp.post("/favoritos/<entity_type>/<int:entity_id>")
@login_required
def toggle_favorite(entity_type, entity_id):
    from ..extensions import db
    models = {"event": Event, "notice": Notice, "schedule": ScheduleItem, "material": Material}
    model = models.get(entity_type)
    obj = db.session.get(model, entity_id) if model else None
    if obj is None:
        abort(404)
    if entity_type == "notice" and obj.published_at > date.today():
        abort(404)
    if entity_type == "schedule" and not current_user.is_admin and obj.class_name != current_user.class_name:
        abort(403)
    if entity_type == "material" and not current_user.is_admin and obj.class_name and obj.class_name != current_user.class_name:
        abort(403)
    fav = Favorite.query.filter_by(user_id=current_user.id, entity_type=entity_type, entity_id=entity_id).first()
    if fav: db.session.delete(fav); flash("Removido dos favoritos.", "info")
    else: db.session.add(Favorite(user_id=current_user.id, entity_type=entity_type, entity_id=entity_id)); flash("Adicionado aos favoritos.", "success")
    db.session.commit(); return redirect(url_for("main.favorites"))


@main_bp.get("/historico")
@login_required
def history():
    today = date.today()
    events = Event.query.filter(Event.event_date < today).order_by(Event.event_date.desc()).limit(100).all()
    notices_history = Notice.query.filter(Notice.published_at < today).order_by(Notice.published_at.desc()).limit(100).all()
    query = ScheduleItem.query.filter(ScheduleItem.due_date < today)
    if not current_user.is_admin:
        query = query.filter_by(class_name=current_user.class_name)
    activities = query.order_by(ScheduleItem.due_date.desc()).limit(100).all()
    return render_template("history.html", events=events, notices=notices_history, activities=activities)


@main_bp.route("/solicitacoes", methods=["GET", "POST"])
@login_required
def requests_page():
    from ..extensions import db
    from ..utils import clean_text
    if request.method == "POST":
        subject=clean_text(request.form.get("subject")); message=clean_text(request.form.get("message"))
        if subject and message: db.session.add(AcademicRequest(user_id=current_user.id, subject=subject[:160], message=message[:3000])); db.session.commit(); flash("Solicitação enviada à equipe administrativa.", "success")
        else: flash("Preencha o assunto e a mensagem.", "error")
        return redirect(url_for("main.requests_page"))
    items=AcademicRequest.query.filter_by(user_id=current_user.id).order_by(AcademicRequest.created_at.desc()).all()
    return render_template("requests.html", requests=items)


@main_bp.get("/calendario-academico")
@login_required
def academic_calendar():
    periods=AcademicPeriod.query.order_by(AcademicPeriod.start_date.asc()).all()
    return render_template("academic_calendar.html", periods=periods)


@main_bp.get("/pesquisa")
@login_required
def global_search():
    query=(request.args.get("q") or "").strip()[:100]; results=[]
    if query:
        like=f"%{query}%"
        for item in Event.query.filter((Event.title.ilike(like)) | (Event.description.ilike(like)) | (Event.location.ilike(like))).limit(15).all(): results.append(("Evento",item.title,item.description or "",url_for("main.agenda")))
        for item in Notice.query.filter(Notice.published_at <= date.today(), ((Notice.title.ilike(like)) | (Notice.content.ilike(like)))).limit(15).all(): results.append(("Aviso",item.title,item.content or "",url_for("main.notices")))
        sq=ScheduleItem.query.filter((ScheduleItem.title.ilike(like)) | (ScheduleItem.subject.ilike(like)) | (ScheduleItem.description.ilike(like)))
        if not current_user.is_admin: sq=sq.filter_by(class_name=current_user.class_name)
        for item in sq.limit(15).all(): results.append(("Atividade",item.title,f"{item.subject} · {item.class_name}",url_for("main.schedules")))
        mq=Material.query.filter((Material.title.ilike(like)) | (Material.subject.ilike(like)) | (Material.description.ilike(like)))
        if not current_user.is_admin: mq=mq.filter((Material.class_name == None) | (Material.class_name == current_user.class_name))
        for item in mq.limit(15).all(): results.append(("Material",item.title,item.description or item.filename,url_for("main.materials")))
    return render_template("search.html", query=query, results=results)
