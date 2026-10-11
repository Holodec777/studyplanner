from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Role(str, Enum):
    student = "student"
    admin = "admin"


class AssignmentStatus(str, Enum):
    planned = "planned"
    in_progress = "in_progress"
    done = "done"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role


class AssignmentFields(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=1000)
    subject: str = Field(min_length=2, max_length=80)
    due_date: date
    priority: Priority = Priority.medium
    status: AssignmentStatus = AssignmentStatus.planned

    @field_validator("title", "subject")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Поле не может быть пустым")
        return value


class AssignmentCreate(AssignmentFields):
    owner_id: int | None = None


class AssignmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    subject: str | None = Field(default=None, min_length=2, max_length=80)
    due_date: date | None = None
    priority: Priority | None = None
    status: AssignmentStatus | None = None
    owner_id: int | None = None

    @field_validator("title", "subject")
    @classmethod
    def trim_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Поле не может быть пустым")
        return value

    @model_validator(mode="after")
    def reject_null_updates(self):
        if not self.model_fields_set:
            raise ValueError("Нужно передать хотя бы одно поле")
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Поля нельзя очищать значением null")
        return self


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    subject: str
    due_date: date
    priority: Priority
    status: AssignmentStatus
    owner_id: int
    owner_username: str


class DashboardStats(BaseModel):
    total: int
    done: int
    overdue: int
    due_soon: int
