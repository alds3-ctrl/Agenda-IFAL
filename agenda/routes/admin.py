from datetime import date, datetime
from pathlib import Path

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from ..attachments import save_uploaded_attachments
from ..extensions import db
from ..models import AcademicPeriod, AcademicRequest, AuditLog, Event, Material, Notice, Notification, ScheduleItem, TimetableEntry, User
from ..utils import CLASS_OPTIONS, admin_required, clean_text, is_student_email, parse_date, valid_matricula, valid_password


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("/")
@admin_required
def index():
    return render_template(
        "admin/index.html",
        users_count=User.query.count(),
        events_count=Event.query.count(),
        schedules_count=ScheduleItem.query.count(),
        notices_count=Notice.query.filter(Notice.published_at <= date.today()).count(),
        scheduled_notices_count=Notice.query.filter(Notice.published_at > date.today()).count(),
        materials_count=Material.query.count(),
        requests_count=AcademicRequest.query.filter_by(status="Aberta").count(),
        recent_audit=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all(),
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
            _audit("Publicou evento", title)
            _notify_students("Novo evento na agenda", title, url_for("main.agenda"), fingerprint_prefix=f"event-pub:{event.id}")
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
            _audit("Editou evento", event.title)
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
    _audit("Removeu evento", event.title)
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
            if class_name not in CLASS_OPTIONS:
                raise ValueError("Selecione uma das turmas disponíveis.")
            item = ScheduleItem(
                class_name=class_name, subject=subject, title=title, term=term,
                activity_type=activity_type, description=description, due_date=due_date,
            )
            db.session.add(item)
            db.session.flush()
            save_uploaded_attachments(item, "schedule_item", request.files.getlist("attachments"))
            _audit("Publicou atividade", f"{title} · {class_name}")
            _notify_students("Nova atividade no cronograma", title, url_for("main.schedules"), class_name, f"schedule-pub:{item.id}")
            db.session.commit()
            flash("Atividade adicionada ao cronograma.", "success")
            return redirect(url_for("admin.schedules"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
    return render_template("admin/schedule_form.html", item=None, page_title="Nova atividade", class_options=CLASS_OPTIONS)


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
            if values["class_name"] not in CLASS_OPTIONS:
                raise ValueError("Selecione uma das turmas disponíveis.")
            for key, value in values.items():
                setattr(item, key, value)
            item.due_date = parse_date(request.form.get("due_date"), "data de entrega")
            save_uploaded_attachments(item, "schedule_item", request.files.getlist("attachments"), request.form.getlist("remove_attachment_ids"))
            _audit("Editou atividade", f"{item.title} · {item.class_name}")
            db.session.commit()
            flash("Atividade atualizada.", "success")
            return redirect(url_for("admin.schedules"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
    return render_template("admin/schedule_form.html", item=item, page_title="Editar atividade", class_options=CLASS_OPTIONS)


@admin_bp.post("/cronogramas/<int:item_id>/excluir")
@admin_required
def delete_schedule(item_id):
    item = db.session.get(ScheduleItem, item_id) or abort(404)
    _audit("Removeu atividade", item.title)
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
            _audit("Publicou/agendou aviso", title)
            if notice.published_at <= date.today():
                _notify_students("Novo aviso institucional", title, url_for("main.notices"), fingerprint_prefix=f"notice:{notice.id}")
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
            _audit("Editou aviso", notice.title)
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
    _audit("Removeu aviso", notice.title)
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
        matricula = clean_text(request.form.get("matricula"))

        if not name or not email or "@" not in email or "." not in email.rsplit("@", 1)[-1] or role not in {"student", "admin"}:
            flash("Informe nome, e-mail válido e perfil.", "error")
        elif role == "student" and not is_student_email(email):
            flash("Contas de estudantes devem usar o domínio @aluno.ifal.edu.br.", "error")
        elif role == "student" and not valid_matricula(matricula):
            flash("A matrícula do estudante deve conter exatamente 10 números.", "error")
        elif role == "student" and class_name not in CLASS_OPTIONS:
            flash("Selecione uma turma válida.", "error")
        elif role == "student" and User.query.filter_by(matricula=matricula).first():
            flash("Esta matrícula já está cadastrada.", "error")
        elif not valid_password(password):
            flash("A senha deve ter pelo menos 8 caracteres, um número e um caractere especial.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Já existe uma conta com esse e-mail.", "error")
        else:
            user = User(name=name, email=email, role=role, class_name=class_name if role == "student" else None, matricula=matricula if role == "student" else None)
            user.set_password(password)
            db.session.add(user)
            _audit("Criou usuário", f"{name} · {role}")
            db.session.commit()
            flash("Usuário criado com sucesso.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", class_options=CLASS_OPTIONS)


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
    _audit("Excluiu usuário", f"{user.name} · {user.email}")
    db.session.delete(user)
    db.session.commit()
    flash("Usuário excluído.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.get("/usuarios")
@admin_required
def users():
    items = User.query.order_by(User.name.asc()).all()
    return render_template("admin/users.html", users=items)


# Recursos administrativos complementares
def _audit(action, details=""):
    db.session.add(AuditLog(user_id=current_user.id if current_user.is_authenticated else None, action=action, details=details[:400]))

def _notify_students(title, message, link, class_name=None, fingerprint_prefix=None):
    query = User.query.filter_by(role="student")
    if class_name: query = query.filter_by(class_name=class_name)
    for student in query.all():
        fingerprint = f"{fingerprint_prefix or title}:{student.id}" if fingerprint_prefix else None
        if fingerprint and Notification.query.filter_by(fingerprint=fingerprint).first(): continue
        db.session.add(Notification(user_id=student.id, title=title, message=message[:400], link=link, fingerprint=fingerprint))


@admin_bp.route("/horarios", methods=["GET", "POST"])
@admin_required
def timetable_admin():
    if request.method == "POST":
        from ..utils import CLASS_OPTIONS
        class_name=clean_text(request.form.get("class_name")); subject=clean_text(request.form.get("subject")); teacher=clean_text(request.form.get("teacher")); room=clean_text(request.form.get("room"))
        try:
            weekday=int(request.form.get("weekday", "0")); start=clean_text(request.form.get("start_time")); end=clean_text(request.form.get("end_time"))
            if class_name not in CLASS_OPTIONS or not subject or weekday not in range(5) or not start or not end or start >= end: raise ValueError("Confira a turma, disciplina, dia e horários informados.")
            db.session.add(TimetableEntry(class_name=class_name, subject=subject, teacher=teacher, room=room, weekday=weekday, start_time=start, end_time=end)); _audit("Criou horário de aula", f"{class_name}: {subject}"); db.session.commit(); flash("Aula adicionada ao horário.", "success")
        except ValueError as error: db.session.rollback(); flash(str(error), "error")
        return redirect(url_for("admin.timetable_admin"))
    entries=TimetableEntry.query.order_by(TimetableEntry.class_name, TimetableEntry.weekday, TimetableEntry.start_time).all()
    return render_template("admin/timetable.html", entries=entries, class_options=CLASS_OPTIONS, weekdays=["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira"])

@admin_bp.post("/horarios/<int:entry_id>/excluir")
@admin_required
def delete_timetable_entry(entry_id):
    item=db.session.get(TimetableEntry,entry_id) or abort(404); _audit("Removeu horário", f"{item.class_name}: {item.subject}"); db.session.delete(item); db.session.commit(); flash("Horário removido.", "success"); return redirect(url_for("admin.timetable_admin"))

@admin_bp.route("/materiais", methods=["GET", "POST"])
@admin_required
def materials_admin():
    if request.method == "POST":
        from ..utils import CLASS_OPTIONS
        uploaded=request.files.get("file"); title=clean_text(request.form.get("title")); class_name=clean_text(request.form.get("class_name")) or None
        if not title or not uploaded or not uploaded.filename: flash("Informe o título e selecione um arquivo.", "error")
        elif class_name and class_name not in CLASS_OPTIONS: flash("Selecione uma turma válida.", "error")
        else:
            raw=uploaded.read(8*1024*1024+1); filename=secure_filename(uploaded.filename)
            if len(raw)>8*1024*1024: flash("O arquivo deve ter até 8 MB.", "error")
            elif not filename: flash("Nome de arquivo inválido.", "error")
            elif Path(filename).suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv"}: flash("Formato de arquivo não permitido.", "error")
            else:
                material=Material(title=title[:160], description=clean_text(request.form.get("description")), subject=clean_text(request.form.get("subject")), class_name=class_name, filename=filename, mimetype=uploaded.mimetype or "application/octet-stream", data=raw)
                db.session.add(material); _audit("Publicou material", title); db.session.commit(); _notify_students("Novo material disponível", title, "/materiais", class_name, f"material:{material.id}"); db.session.commit(); flash("Material publicado.", "success")
        return redirect(url_for("admin.materials_admin"))
    return render_template("admin/materials.html", materials=Material.query.order_by(Material.created_at.desc()).all(), class_options=CLASS_OPTIONS)

@admin_bp.post("/materiais/<int:material_id>/excluir")
@admin_required
def delete_material(material_id):
    item=db.session.get(Material,material_id) or abort(404); _audit("Removeu material", item.title); db.session.delete(item); db.session.commit(); flash("Material removido.", "success"); return redirect(url_for("admin.materials_admin"))

@admin_bp.route("/calendario-academico", methods=["GET", "POST"])
@admin_required
def academic_periods_admin():
    if request.method == "POST":
        try:
            title=clean_text(request.form.get("title")); start=parse_date(request.form.get("start_date"), "data inicial"); end=parse_date(request.form.get("end_date"), "data final")
            if not title or end < start: raise ValueError("Informe um título e um período válido.")
            db.session.add(AcademicPeriod(title=title, description=clean_text(request.form.get("description")), start_date=start, end_date=end, kind=clean_text(request.form.get("kind")) or "Período letivo")); _audit("Criou período acadêmico", title); db.session.commit(); flash("Período acadêmico cadastrado.", "success")
        except ValueError as error: db.session.rollback(); flash(str(error), "error")
        return redirect(url_for("admin.academic_periods_admin"))
    return render_template("admin/academic_periods.html", periods=AcademicPeriod.query.order_by(AcademicPeriod.start_date).all())

@admin_bp.post("/calendario-academico/<int:period_id>/excluir")
@admin_required
def delete_academic_period(period_id):
    item=db.session.get(AcademicPeriod,period_id) or abort(404); _audit("Removeu período acadêmico", item.title); db.session.delete(item); db.session.commit(); flash("Período removido.", "success"); return redirect(url_for("admin.academic_periods_admin"))

@admin_bp.get("/solicitacoes")
@admin_required
def requests_admin():
    items=AcademicRequest.query.order_by(AcademicRequest.created_at.desc()).all(); return render_template("admin/requests.html", requests=items)

@admin_bp.post("/solicitacoes/<int:request_id>")
@admin_required
def update_request(request_id):
    item=db.session.get(AcademicRequest,request_id) or abort(404); item.status=request.form.get("status") if request.form.get("status") in {"Aberta","Em análise","Respondida","Encerrada"} else "Aberta"; item.admin_response=clean_text(request.form.get("admin_response"))[:3000]; item.updated_at=datetime.utcnow(); _audit("Atualizou solicitação", f"Solicitação #{item.id}: {item.status}"); db.session.add(Notification(user_id=item.user_id, title="Sua solicitação foi atualizada", message=f"{item.subject}: {item.status}", link=url_for("main.requests_page"))); db.session.commit(); flash("Solicitação atualizada.", "success"); return redirect(url_for("admin.requests_admin"))

@admin_bp.get("/historico")
@admin_required
def audit_history():
    items=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(250).all(); return render_template("admin/audit.html", logs=items)
