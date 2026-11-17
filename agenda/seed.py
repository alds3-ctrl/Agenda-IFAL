from datetime import date, timedelta

from .extensions import db
from .models import Event, Notice, ScheduleItem, User


def seed_demo_data():
    """Cria contas e registros demonstrativos somente quando o banco está vazio."""
    if User.query.first():
        return

    admin = User(name="Administrador Agenda IFAL", email="admin@agendaifal.local", role="admin")
    admin.set_password("Admin123!")
    student = User(
        name="Estudante de demonstração",
        email="aluno@agendaifal.local",
        role="student",
        class_name="3º ano (exemplo)",
    )
    student.set_password("Aluno123!")
    db.session.add_all([admin, student])
    db.session.flush()

    today = date.today()
    db.session.add_all([
        Event(
            title="Reunião de orientação acadêmica",
            description="Encontro demonstrativo para apresentar orientações e informações importantes aos estudantes.",
            event_date=today + timedelta(days=7),
            start_time="09:00",
            end_time="10:00",
            location="Auditório do campus",
            category="Institucional",
            author=admin,
        ),
        Event(
            title="Atividade de integração estudantil",
            description="Exemplo de evento que poderá ser substituído pelos eventos oficiais do campus.",
            event_date=today + timedelta(days=14),
            start_time="14:00",
            location="Pátio principal",
            category="Evento",
            author=admin,
        ),
        Notice(
            title="Bem-vindo ao Agenda IFAL",
            content="Este é um aviso de demonstração. A administração poderá publicar comunicados, orientações e atualizações importantes por aqui.",
            published_at=today,
            is_pinned=True,
            author=admin,
        ),
        ScheduleItem(
            class_name="3º ano (exemplo)",
            term="1º Bimestre",
            subject="Exemplo de disciplina",
            title="Atividade demonstrativa",
            description="Registro de exemplo. O administrador pode editar ou excluir este item e cadastrar as atividades reais da turma.",
            due_date=today + timedelta(days=10),
            activity_type="Trabalho",
        ),
    ])
    db.session.commit()
