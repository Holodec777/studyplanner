from datetime import date, timedelta


def login(client, username="student", password="student123"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_login_and_current_user(client):
    headers = login(client)
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "student"
    assert response.json()["role"] == "student"


def test_student_can_create_update_and_delete_own_assignment(client):
    headers = login(client)
    payload = {
        "title": "Подготовить доклад",
        "subject": "История",
        "due_date": str(date.today() + timedelta(days=2)),
        "priority": "high",
    }
    created = client.post("/api/assignments", json=payload, headers=headers)
    assert created.status_code == 201
    assignment_id = created.json()["id"]
    assert created.json()["owner_username"] == "student"

    updated = client.patch(f"/api/assignments/{assignment_id}", json={"status": "done"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["status"] == "done"

    deleted = client.delete(f"/api/assignments/{assignment_id}", headers=headers)
    assert deleted.status_code == 204


def test_student_cannot_assign_or_change_another_students_task(client):
    student_headers = login(client)
    task = {"title": "Подготовить доклад", "subject": "История", "due_date": str(date.today() + timedelta(days=2)), "owner_id": 2}
    forbidden = client.post("/api/assignments", json=task, headers=student_headers)
    assert forbidden.status_code == 403

    admin_headers = login(client, "admin", "admin123")
    created = client.post("/api/assignments", json=task, headers=admin_headers)
    assignment_id = created.json()["id"]
    assert client.patch(f"/api/assignments/{assignment_id}", json={"status": "done"}, headers=student_headers).status_code == 404
    assert client.delete(f"/api/assignments/{assignment_id}", headers=student_headers).status_code == 404


def test_student_list_is_scoped_and_admin_can_assign(client):
    admin_headers = login(client, "admin", "admin123")
    task = {"title": "Задача другого ученика", "subject": "Физика", "due_date": str(date.today()), "owner_id": 2}
    assert client.post("/api/assignments", json=task, headers=admin_headers).status_code == 201

    student_headers = login(client)
    assert client.get("/api/assignments", headers=student_headers).json() == []
    users = client.get("/api/users", headers=admin_headers)
    assert users.status_code == 200
    assert len(users.json()) == 2
    assert client.get("/api/users", headers=student_headers).status_code == 403

    response = client.post(
        "/api/assignments",
        json={"title": "Проверить проект", "subject": "Информатика", "due_date": str(date.today()), "owner_id": 2},
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["owner_username"] == "other"
    assert len(client.get("/api/assignments", headers=admin_headers).json()) == 2


def test_invalid_assignment_is_rejected(client):
    headers = login(client)
    response = client.post(
        "/api/assignments",
        json={"title": "  ", "subject": "История", "due_date": str(date.today())},
        headers=headers,
    )
    assert response.status_code == 422
