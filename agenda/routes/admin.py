from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from ..attachments import save_uploaded_attachments
from ..extensions import db
from ..models import Event, Notice, ScheduleItem, User
from ..utils import admin_required, clean_text, is_student_email, parse_date


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("/")
@admin_required
def index():
    return render_template(
        "admin/index.html",
        users_count=User.query.count(),
        events_count=Event.query.count(),
        schedules_count=ScheduleItem.query.count(),
        notices_count=Notice.query.count(),
    )


@admin_bp.route("/eventos/novo", methods=["GET", "POST"])
@admin_required
def new_event():
    if request.method == "POST":
        try:
            title = clean_text(request.form.get("title"))
            description = clean_text(request.form.get("description"))
            location = clean_text(request.form.get("location"))
            category = clean_text(request.form.get("category")) or "Acadêmico"
            event_date = parse_date(request.form.get("event_date"), "data do evento")
            start_time = clean_text(request.form.get("start_time")) or None
            end_time = clean_text(request.form.get("end_time")) or None
            if not title or not description:
                raise ValueError("Preencha o título e a descrição do evento.")
            if len(title) > 140:
                raise ValueError("O título deve ter no máximo 140 caracteres.")
            event = Event(
                title=title, description=description, event_date=event_date,
                start_time=start_time, end_time=end_time, location=location,
                category=category, author=current_user,
            )
            db.session.add(event)
            db.session.flush()
            save_uploaded_attachments(event, "event", request.files.getlist("attachments"))
            db.session.commit()
            flash("Evento cadastrado com sucesso.", "success")
            return redirect(url_for("admin.events"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
    return render_template("admin/event_form.html", event=None, page_title="Novo evento")


@admin_bp.route("/eventos/<int:event_id>/editar", methods=["GET", "POST"])
@admin_required
def edit_event(event_id):
    event = db.session.get(Event, event_id) or abort(404)
    if request.method == "POST":
        try:
            title = clean_text(request.form.get("title"))
            description = clean_text(request.form.get("description"))
            if not title or not description:
                raise ValueError("Preencha o título e a descrição do evento.")
            event.title = title
            event.description = description
            event.event_date = parse_date(request.form.get("event_date"), "data do evento")
            event.start_time = clean_text(request.form.get("start_time")) or None
            event.end_time = clean_text(request.form.get("end_time")) or None
            event.location = clean_text(request.form.get("location"))
            event.category = clean_text(request.form.get("category")) or "Acadêmico"
            save_uploaded_attachments(event, "event", request.files.getlist("attachments"), request.form.getlist("remove_attachment_ids"))
            db.session.commit()
            flash("Evento atualizado com sucesso.", "success")
            return redirect(url_for("admin.events"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
    return render_template("admin/event_form.html", event=event, page_title="Editar evento")


@admin_bp.post("/eventos/<int:event_id>/excluir")
@admin_required
def delete_event(event_id):
    event = db.session.get(Event, event_id) or abort(404)
    db.session.delete(event)
    db.session.commit()
    flash("Evento excluído.", "success")
    return redirect(url_for("admin.events"))


@admin_bp.get("/eventos")
@admin_required
def events():
    items = Event.query.order_by(Event.event_date.desc()).all()
    return render_template("admin/events.html", events=items)


@admin_bp.route("/cronogramas/novo", methods=["GET", "POST"])
@admin_required
def new_schedule():
    if request.method == "POST":
        try:
            class_name = clean_text(request.form.get("class_name"))
            subject = clean_text(request.form.get("subject"))
            title = clean_text(request.form.get("title"))
            term = clean_text(request.form.get("term"))
            activity_type = clean_text(request.form.get("activity_type")) or "Atividade"
            description = clean_text(request.form.get("description"))
            due_date = parse_date(request.form.get("due_date"), "data de entrega")
            if not all([class_name, subject, title, term]):
                raise ValueError("Preencha turma, disciplina, atividade e bimestre.")
            item = ScheduleItem(
                class_name=class_name, subject=subject, title=title, term=term,
                activity_type=activity_type, description=description, due_date=due_date,
            )
            db.session.add(item)
            db.session.flush()
            save_uploaded_attachments(item, "schedule_item", request.files.getlist("attachments"))
            db.session.commit()
            flash("Atividade adicionada ao cronograma.", "success")
            return redirect(url_for("admin.schedules"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
    return render_template("admin/schedule_form.html", item=None, page_title="Nova atividade")


@admin_bp.route("/cronogramas/<int:item_id>/editar", methods=["GET", "POST"])
@admin_required
def edit_schedule(item_id):
    item = db.session.get(ScheduleItem, item_id) or abort(404)
    if request.method == "POST":
        try:
            values = {
                "class_name": clean_text(request.form.get("class_name")),
                "subject": clean_text(request.form.get("subject")),
                "title": clean_text(request.form.get("title")),
                "term": clean_text(request.form.get("term")),
                "activity_type": clean_text(request.form.get("activity_type")) or "Atividade",
                "description": clean_text(request.form.get("description")),
            }
            if not all([values["class_name"], values["subject"], values["title"], values["term"]]):
                raise ValueError("Preencha turma, disciplina, atividade e bimestre.")
            for key, value in values.items():
                setattr(item, key, value)
            item.due_date = parse_date(request.form.get("due_date"), "data de entrega")
            save_uploaded_attachments(item, "schedule_item", request.files.getlist("attachments"), request.form.getlist("remove_attachment_ids"))
            db.session.commit()
            flash("Atividade atualizada.", "success")
            return redirect(url_for("admin.schedules"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
    return render_template("admin/schedule_form.html", item=item, page_title="Editar atividade")


@admin_bp.post("/cronogramas/<int:item_id>/excluir")
@admin_required
def delete_schedule(item_id):
    item = db.session.get(ScheduleItem, item_id) or abort(404)
    db.session.delete(item)
    db.session.commit()
    flash("Atividade removida do cronograma.", "success")
    return redirect(url_for("admin.schedules"))


@admin_bp.get("/cronogramas")
@admin_required
def schedules():
    items = ScheduleItem.query.order_by(ScheduleItem.due_date.desc()).all()
    return render_template("admin/schedules.html", items=items)


@admin_bp.route("/avisos/novo", methods=["GET", "POST"])
@admin_required
def new_notice():
    if request.method == "POST":
        title = clean_text(request.form.get("title"))
        content = clean_text(request.form.get("content"))
        try:
            published_at = parse_date(request.form.get("published_at"), "data de publicação")
            if not title or not content:
                raise ValueError("Preencha o título e o conteúdo do aviso.")
            notice = Notice(
                title=title, content=content, published_at=published_at,
                is_pinned=bool(request.form.get("is_pinned")), author=current_user,
            )
            db.session.add(notice)
            db.session.flush()
            save_uploaded_attachments(notice, "notice", request.files.getlist("attachments"))
            db.session.commit()
            flash("Aviso publicado com sucesso.", "success")
            return redirect(url_for("admin.notices"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
    return render_template("admin/notice_form.html", notice=None, page_title="Novo aviso")


@admin_bp.route("/avisos/<int:notice_id>/editar", methods=["GET", "POST"])
@admin_required
def edit_notice(notice_id):
    notice = db.session.get(Notice, notice_id) or abort(404)
    if request.method == "POST":
        try:
            title = clean_text(request.form.get("title"))
            content = clean_text(request.form.get("content"))
            if not title or not content:
                raise ValueError("Preencha o título e o conteúdo do aviso.")
            notice.title = title
            notice.content = content
            notice.published_at = parse_date(request.form.get("published_at"), "data de publicação")
            notice.is_pinned = bool(request.form.get("is_pinned"))
            save_uploaded_attachments(notice, "notice", request.files.getlist("attachments"), request.form.getlist("remove_attachment_ids"))
            db.session.commit()
            flash("Aviso atualizado.", "success")
            return redirect(url_for("admin.notices"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
    return render_template("admin/notice_form.html", notice=notice, page_title="Editar aviso")


@admin_bp.post("/avisos/<int:notice_id>/excluir")
@admin_required
def delete_notice(notice_id):
    notice = db.session.get(Notice, notice_id) or abort(404)
    db.session.delete(notice)
    db.session.commit()
    flash("Aviso excluído.", "success")
    return redirect(url_for("admin.notices"))


@admin_bp.get("/avisos")
@admin_required
def notices():
    items = Notice.query.order_by(Notice.published_at.desc()).all()
    return render_template("admin/notices.html", notices=items)


@admin_bp.route("/usuarios/novo", methods=["GET", "POST"])
@admin_required
def new_user():
    if request.method == "POST":
        name = clean_text(request.form.get("name"))
        email = clean_text(request.form.get("email")).lower()
        role = clean_text(request.form.get("role"))
        class_name = clean_text(request.form.get("class_name")) or None
        password = request.form.get("password", "")

        if not name or not email or "@" not in email or "." not in email.rsplit("@", 1)[-1] or role not in {"student", "admin"}:
            flash("Informe nome, e-mail válido e perfil.", "error")
        elif role == "student" and not is_student_email(email):
            flash("Contas de estudantes devem usar o domínio @aluno.ifal.edu.br.", "error")
        elif len(password) < 8:
            flash("A senha deve ter pelo menos 8 caracteres.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Já existe uma conta com esse e-mail.", "error")
        else:
            user = User(name=name, email=email, role=role, class_name=class_name if role == "student" else None)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Usuário criado com sucesso.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html")


@admin_bp.post("/usuarios/<int:user_id>/excluir")
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.id == current_user.id:
        flash("Você não pode excluir a própria conta enquanto está conectado.", "error")
        return redirect(url_for("admin.users"))
    if user.is_admin and User.query.filter_by(role="admin").count() <= 1:
        flash("O sistema precisa manter pelo menos um administrador.", "error")
        return redirect(url_for("admin.users"))
    db.session.delete(user)
    db.session.commit()
    flash("Usuário excluído.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.get("/usuarios")
@admin_required
def users():
    items = User.query.order_by(User.name.asc()).all()
    return render_template("admin/users.html", users=items)
