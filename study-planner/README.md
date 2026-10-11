# Маяк — учебный планер

Локальное веб-приложение для планирования учебных заданий. Ученик ведет собственный список задач и сроков, а администратор видит общий план и может назначать задачи ученикам.

## Основные возможности

- Вход с ролями ученика и администратора.
- Создание, изменение, поиск, фильтрация по статусу и удаление учебных задач.
- Приоритет, предмет, срок и сводка по просроченным и выполненным задачам.
- Ограничение доступа: ученик видит и меняет только свои задачи.
- PostgreSQL, Alembic-миграции и API-документация FastAPI.

## Стек

Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL 16, Alembic, HTML/CSS/JavaScript, pytest, Docker Compose.

## Структура

~~~text
study-planner/
├── app/
│   ├── auth.py             # пароли, токены и проверка пользователя
│   ├── db.py               # подключение к базе и сессии
│   ├── main.py             # REST API и раздача интерфейса
│   ├── models.py           # SQLAlchemy-модели
│   ├── schemas.py          # валидация запросов и ответов
│   ├── seed.py             # демо-аккаунты и стартовые задачи
│   └── static/              # веб-интерфейс
├── alembic/                 # конфигурация и миграции
├── docs/                    # user story, модель данных, план презентации
├── tests/                   # API-тесты на отдельной SQLite-базе
├── compose.yaml
├── Dockerfile
└── requirements.txt
~~~

## Переменные окружения

Создай локальный файл `.env` из `.env.example`. В `compose.yaml` для контейнера база подключается к PostgreSQL внутри Docker Compose.

| Переменная | Назначение | Пример |
|---|---|---|
| `DATABASE_URL` | URL базы данных для запуска приложения на компьютере | `postgresql+psycopg://study_planner:study_planner_local@localhost:5433/study_planner` |
| `SECRET_KEY` | Ключ подписи токенов | длинная случайная строка |

Compose задает `DATABASE_URL` для контейнера, а ключ берет из `.env`. При прямом запуске без `DATABASE_URL` приложение использует локальный SQLite-файл `study_planner.db`.

Демо-пароли предназначены только для локальной учебной демонстрации. Не выставляй этот проект в интернет без настройки собственного ключа и учетных записей.

## Запуск

Нужен установленный Docker Desktop с запущенным движком. В PowerShell:

~~~powershell
Copy-Item .env.example .env
docker compose up --build
~~~

Открой [http://localhost:8000](http://localhost:8000). При старте Compose ждет готовности PostgreSQL, применяет миграции Alembic и создает демо-данные. Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs).

Чтобы остановить приложение, нажми `Ctrl+C`. `docker compose down` останавливает контейнеры и сохраняет данные. Удалить контейнеры вместе с данными можно командой `docker compose down -v`.

## Демо-аккаунты

| Роль | Логин | Пароль |
|---|---|---|
| Ученик | `student` | `student123` |
| Администратор | `admin` | `admin123` |

## Тесты

В Docker Compose:

~~~powershell
docker compose exec app pytest
~~~

Также тесты можно запустить локально после установки зависимостей:

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
~~~

Каждый тест использует отдельную временную базу и не меняет данные приложения.

## API

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/api/auth/login` | Войти и получить Bearer-токен |
| `GET` | `/api/auth/me` | Текущий пользователь и его роль |
| `GET` | `/api/users` | Список учеников, только для администратора |
| `GET` | `/api/assignments` | Список задач с фильтрами `status` и `q` |
| `POST` | `/api/assignments` | Создать задачу |
| `PATCH` | `/api/assignments/{id}` | Изменить задачу или ее статус |
| `DELETE` | `/api/assignments/{id}` | Удалить задачу |
| `GET` | `/api/dashboard` | Сводка по задачам |
| `GET` | `/api/health` | Проверка приложения и соединения с БД |

## Материалы к защите

- [User story и правила доступа](docs/USER_STORIES.md)
- [Модель данных](docs/DATA_MODEL.md)
- [План презентации](docs/PRESENTATION.md)
