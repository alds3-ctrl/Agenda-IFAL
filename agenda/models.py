from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    matricula = db.Column(db.String(10), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    class_name = db.Column(db.String(80), nullable=True)
    profile_photo = db.Column(db.LargeBinary, nullable=True)
    profile_photo_mimetype = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    events = db.relationship("Event", back_populates="author", lazy=True)
    notices = db.relationship("Notice", back_populates="author", lazy=True)

    @property
    def is_admin(self):
        return self.role == "admin"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=False)
    event_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.String(5), nullable=True)
    end_time = db.Column(db.String(5), nullable=True)
    location = db.Column(db.String(120), nullable=True)
    category = db.Column(db.String(40), nullable=False, default="Acadêmico")
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    author = db.relationship("User", back_populates="events")
    attachments = db.relationship(
        "Attachment", back_populates="event", cascade="all, delete-orphan",
        foreign_keys="Attachment.event_id", lazy="selectin",
    )

    @property
    def is_upcoming(self):
        return self.event_date >= date.today()


class ScheduleItem(db.Model):
    __tablename__ = "schedule_items"

    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(80), nullable=False, index=True)
    term = db.Column(db.String(20), nullable=False, default="1º Bimestre")
    subject = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=False, index=True)
    activity_type = db.Column(db.String(40), nullable=False, default="Trabalho")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    attachments = db.relationship(
        "Attachment", back_populates="schedule_item", cascade="all, delete-orphan",
        foreign_keys="Attachment.schedule_item_id", lazy="selectin",
    )


class Notice(db.Model):
    __tablename__ = "notices"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    content = db.Column(db.Text, nullable=False)
    published_at = db.Column(db.Date, nullable=False, default=date.today, index=True)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    author = db.relationship("User", back_populates="notices")
    attachments = db.relationship(
        "Attachment", back_populates="notice", cascade="all, delete-orphan",
        foreign_keys="Attachment.notice_id", lazy="selectin",
    )


class Attachment(db.Model):
    """Arquivo anexado a um evento, atividade de cronograma ou aviso."""
    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True)
    schedule_item_id = db.Column(db.Integer, db.ForeignKey("schedule_items.id", ondelete="CASCADE"), nullable=True, index=True)
    notice_id = db.Column(db.Integer, db.ForeignKey("notices.id", ondelete="CASCADE"), nullable=True, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    event = db.relationship("Event", back_populates="attachments", foreign_keys=[event_id])
    schedule_item = db.relationship("ScheduleItem", back_populates="attachments", foreign_keys=[schedule_item_id])
    notice = db.relationship("Notice", back_populates="attachments", foreign_keys=[notice_id])


class EmailVerification(db.Model):
    """Cadastro estudantil pendente de confirmação do e-mail institucional."""
    __tablename__ = "email_verifications"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    class_name = db.Column(db.String(80), nullable=True)
    matricula = db.Column(db.String(10), nullable=True, index=True)
    code_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    request_ip = db.Column(db.String(45), nullable=True, index=True)
    last_sent_at = db.Column(db.DateTime, nullable=False)
    verified_at = db.Column(db.DateTime, nullable=True)
    setup_token_hash = db.Column(db.String(64), nullable=True, index=True)
    setup_expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class EmailChangeVerification(db.Model):
    __tablename__ = "email_change_verifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    new_email = db.Column(db.String(160), nullable=False, unique=True)
    code_hash = db.Column(db.String(64), nullable=False)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    expires_at = db.Column(db.DateTime, nullable=False)
    last_sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user = db.relationship("User")


class PasswordReset(db.Model):
    """Verificação temporária por e-mail para redefinição de senha."""
    __tablename__ = "password_resets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    code_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    last_sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reset_token_hash = db.Column(db.String(64), nullable=True, index=True)
    reset_token_expires_at = db.Column(db.DateTime, nullable=True)
    pending_password_hash = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship("User")


class PersonalTask(db.Model):
    __tablename__ = "personal_tasks"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True, index=True)
    priority = db.Column(db.String(12), nullable=False, default="Média")
    completed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship("User")


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.String(400), nullable=False)
    link = db.Column(db.String(255), nullable=True)
    fingerprint = db.Column(db.String(190), nullable=True, unique=True)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    user = db.relationship("User")


class TimetableEntry(db.Model):
    __tablename__ = "timetable_entries"
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(80), nullable=False, index=True)
    weekday = db.Column(db.Integer, nullable=False)  # 0=segunda
    start_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    teacher = db.Column(db.String(120), nullable=True)
    room = db.Column(db.String(80), nullable=True)


class Material(db.Model):
    __tablename__ = "materials"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subject = db.Column(db.String(100), nullable=True)
    class_name = db.Column(db.String(80), nullable=True, index=True)
    filename = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(100), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class Favorite(db.Model):
    __tablename__ = "favorites"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = db.Column(db.String(30), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "entity_type", "entity_id", name="uq_user_favorite"),)
    user = db.relationship("User")


class AcademicRequest(db.Model):
    __tablename__ = "academic_requests"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Aberta")
    admin_response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    user = db.relationship("User")


class AcademicPeriod(db.Model):
    __tablename__ = "academic_periods"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    kind = db.Column(db.String(40), nullable=False, default="Período letivo")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.String(400), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    user = db.relationship("User")
