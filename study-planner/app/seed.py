from datetime import date, timedelta

from sqlalchemy import select

from app.auth import hash_password
from app.db import SessionLocal
from app.models import Assignment, User


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            return

        student = User(username="student", password_hash=hash_password("student123"), role="student")
        admin = User(username="admin", password_hash=hash_password("admin123"), role="admin")
        db.add_all([student, admin])
        db.flush()

        today = date.today()
        db.add_all(
            [
                Assignment(title="Прочитать главу 4", description="Сделать краткий конспект", subject="Биология", due_date=today + timedelta(days=1), priority="high", status="in_progress", owner_id=student.id),
                Assignment(title="Решить задачи 12–18", description="Проверить ответы по учебнику", subject="Математика", due_date=today + timedelta(days=3), priority="medium", status="planned", owner_id=student.id),
                Assignment(title="Подготовить эссе", description="Тема: технологии в образовании", subject="Русский язык", due_date=today + timedelta(days=7), priority="low", status="planned", owner_id=student.id),
            ]
        )
        db.commit()


if __name__ == "__main__":
    seed()
