from datetime import date, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, verify_password
from app.db import get_db
from app.models import Assignment, User
from app.schemas import (
    AssignmentCreate,
    AssignmentOut,
    AssignmentStatus,
    AssignmentUpdate,
    DashboardStats,
    LoginRequest,
    TokenResponse,
    UserOut,
)

app = FastAPI(title="Маяк — учебный планер", version="1.0.0")
STATIC_DIR = Path(__file__).parent / "static"


def require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Доступно только администратору")


def get_assignment(db: Session, assignment_id: int, user: User) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if user.role != "admin" and assignment.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return assignment


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return TokenResponse(access_token=create_access_token(user.id))


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@app.get("/api/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    return list(db.scalars(select(User).where(User.is_active.is_(True), User.role == "student").order_by(User.username)))


@app.get("/api/assignments", response_model=list[AssignmentOut])
def list_assignments(
    status_filter: AssignmentStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Assignment).join(User, Assignment.owner_id == User.id)
    if user.role != "admin":
        query = query.where(Assignment.owner_id == user.id)
    if status_filter:
        query = query.where(Assignment.status == status_filter.value)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        query = query.where(or_(Assignment.title.ilike(pattern), Assignment.subject.ilike(pattern)))
    query = query.order_by(Assignment.due_date, Assignment.id).limit(limit)
    return list(db.scalars(query))


@app.post("/api/assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.owner_id is not None and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нельзя назначить задачу другому пользователю")
    owner_id = payload.owner_id if payload.owner_id is not None else user.id
    owner = db.get(User, owner_id)
    if owner is None or not owner.is_active or (user.role == "admin" and owner.role != "student"):
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    assignment = Assignment(**payload.model_dump(exclude={"owner_id"}), owner_id=owner_id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@app.patch("/api/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assignment = get_assignment(db, assignment_id, user)
    changes = payload.model_dump(exclude_unset=True)
    if "owner_id" in changes:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Назначать задачи может только администратор")
        owner = db.get(User, changes["owner_id"])
        if owner is None or not owner.is_active or owner.role != "student":
            raise HTTPException(status_code=404, detail="Пользователь не найден")
    for name, value in changes.items():
        setattr(assignment, name, value.value if hasattr(value, "value") else value)
    db.commit()
    db.refresh(assignment)
    return assignment


@app.delete("/api/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assignment = get_assignment(db, assignment_id, user)
    db.delete(assignment)
    db.commit()


@app.get("/api/dashboard", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    scope = [] if user.role == "admin" else [Assignment.owner_id == user.id]
    today = date.today()
    base = select(func.count()).select_from(Assignment).where(*scope)

    def count(*conditions):
        return db.scalar(base.where(*conditions)) or 0

    return DashboardStats(
        total=count(),
        done=count(Assignment.status == "done"),
        overdue=count(Assignment.due_date < today, Assignment.status != "done"),
        due_soon=count(Assignment.due_date.between(today, today + timedelta(days=7)), Assignment.status != "done"),
    )


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
