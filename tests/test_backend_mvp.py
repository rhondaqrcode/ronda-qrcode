from fastapi.testclient import TestClient
from io import BytesIO
from PIL import Image

from backend.app.main import app


def test_backend_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_backend_login_and_metrics() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/auth/login",
            data={"username": "admin@facilities.local", "password": "admin123"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        metrics = client.get(
            "/dashboard/metrics",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert metrics.status_code == 200
    assert "active_employees" in metrics.json()


def test_backend_report_generation() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/auth/login",
            data={"username": "admin@facilities.local", "password": "admin123"},
        )
        token = login.json()["access_token"]

        response = client.post(
            "/reports",
            json={"report_type": "productivity", "title": "Relatorio teste"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    assert response.json()["file_url"].endswith(".pdf")


def test_create_location() -> None:
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/locations",
            json={
                "name": "Cliente Real Teste",
                "address": "Rua Operacional, 100",
                "city": "Sao Paulo",
            },
            headers=headers,
        )

    assert response.status_code == 201
    assert response.json()["name"] == "Cliente Real Teste"


def test_admin_can_deactivate_employee_and_location() -> None:
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        unique_email = f"desativar.{len(token)}.{id(client)}@example.com"

        employee = client.post(
            "/employees",
            json={
                "name": "Funcionario Para Desativar",
                "email": unique_email,
                "password": "123456",
                "phone": "11988887777",
                "position": "Auxiliar de limpeza",
                "role": "employee",
            },
            headers=headers,
        )
        assert employee.status_code == 201
        employee_id = employee.json()["id"]

        deleted_employee = client.delete(f"/employees/{employee_id}", headers=headers)
        assert deleted_employee.status_code == 204
        active_employee_ids = {
            item["id"] for item in client.get("/employees", headers=headers).json()
        }
        assert employee_id not in active_employee_ids

        location = client.post(
            "/locations",
            json={
                "name": "Local Para Desativar",
                "address": "Rua de Teste, 200",
                "city": "Sao Paulo",
            },
            headers=headers,
        )
        assert location.status_code == 201

        deleted_location = client.delete(f"/locations/{location.json()['id']}", headers=headers)
        assert deleted_location.status_code == 204


def test_employee_login_is_case_insensitive() -> None:
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        suffix = id(client)

        created = client.post(
            "/employees",
            json={
                "name": "Funcionario Login Case",
                "email": f"Funcionario.Case.{suffix}@Example.COM",
                "password": "123456",
                "phone": "",
                "position": "Auxiliar de limpeza",
                "role": "employee",
            },
            headers=headers,
        )
        assert created.status_code == 201

        login = client.post(
            "/auth/login",
            data={
                "username": f"funcionario.case.{suffix}@example.com",
                "password": "123456",
            },
        )
        assert login.status_code == 200
        assert login.json()["user"]["role"] == "employee"


def test_patrol_qr_flow() -> None:
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        location_id = client.get("/locations", headers=headers).json()[0]["id"]
        qr_code = f"RONDA-TESTE-{id(client)}"

        point = client.post(
            "/patrol/points",
            json={
                "location_id": location_id,
                "name": "Portaria principal",
                "qr_code": qr_code,
                "instructions": "Conferir acesso e limpeza.",
            },
            headers=headers,
        )
        assert point.status_code == 201
        assert point.json()["qr_code"] == qr_code

        scan = client.post(
            "/patrol/scans",
            json={"qr_code": qr_code, "notes": "Ronda realizada."},
            headers=headers,
        )
        assert scan.status_code == 201
        assert scan.json()["point"]["name"] == "Portaria principal"
        assert scan.json()["employee"]["name"] == "Administrador"

        scans = client.get("/patrol/scans", headers=headers)
        assert scans.status_code == 200
        assert any(item["qr_code"] == qr_code for item in scans.json())


def test_employee_operational_flow() -> None:
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        locations = client.get("/locations", headers=headers)
        assert locations.status_code == 200
        location_id = locations.json()[0]["id"]

        check_in = client.post(
            "/attendance/check-in",
            json={
                "location_id": location_id,
                "latitude": -23.55052,
                "longitude": -46.633308,
                "notes": "Inicio da rotina",
            },
            headers=headers,
        )
        assert check_in.status_code == 201
        attendance_id = check_in.json()["id"]
        assert check_in.json()["check_in_latitude"] == -23.55052
        assert check_in.json()["check_in_longitude"] == -46.633308

        current = client.get("/attendance/current", headers=headers)
        assert current.status_code == 200
        assert current.json()["id"] == attendance_id

        checklist = client.post(
            "/checklists",
            json={
                "location_id": location_id,
                "title": "Limpeza teste",
                "shift": "Diurno",
                "observations": "Checklist criado pelo teste",
                "tasks": [{"description": "Limpar area comum"}],
            },
            headers=headers,
        )
        assert checklist.status_code == 201
        checklist_body = checklist.json()

        task = client.patch(
            f"/checklists/{checklist_body['id']}/tasks/{checklist_body['tasks'][0]['id']}",
            json={"is_done": True},
            headers=headers,
        )
        assert task.status_code == 200
        assert task.json()["status"] == "completed"

        occurrence = client.post(
            "/occurrences",
            json={
                "location_id": location_id,
                "title": "Ocorrencia teste",
                "description": "Registro operacional criado pelo teste",
                "severity": "medium",
            },
            headers=headers,
        )
        assert occurrence.status_code == 201

        photo = client.post(
            "/photos",
            files={"file": ("foto.png", _png_bytes(), "image/png")},
            data={"entity_type": "attendance", "entity_id": str(attendance_id)},
            headers=headers,
        )
        assert photo.status_code == 201
        assert photo.json()["url"].startswith("/uploads/photos/")

        check_out = client.patch(f"/attendance/{attendance_id}/check-out", headers=headers)
        assert check_out.status_code == 200
        assert check_out.json()["status"] == "checked_out"

        current_after_checkout = client.get("/attendance/current", headers=headers)
        assert current_after_checkout.status_code == 200
        assert current_after_checkout.json() is None


def _login(client: TestClient) -> str:
    login = client.post(
        "/auth/login",
        data={"username": "admin@facilities.local", "password": "admin123"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (16, 16), color="white").save(buffer, format="PNG")
    return buffer.getvalue()
