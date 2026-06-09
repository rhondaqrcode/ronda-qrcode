from uuid import uuid4
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app


def test_qr_shift_flow_generates_report() -> None:
    with TestClient(app) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        qr_code = f"PONTO_TESTE_{uuid4().hex[:8].upper()}"

        point = client.post(
            "/ronda/pontos",
            json={
                "nome_ponto": "Ponto teste automatizado",
                "codigo_qr": qr_code,
                "descricao": "Ponto criado pelo teste.",
                "ordem": 99,
                "meta_passagens_turno": 2,
                "carencia_minutos": 45,
            },
            headers=headers,
        )
        assert point.status_code == 201

        started = client.post("/ronda/turnos/iniciar", headers=headers)
        assert started.status_code == 201
        assert started.json()["status"] == "active"

        reading = client.post(
            "/ronda/leituras",
            headers=headers,
            data={"codigo_qr": qr_code, "observacao": "Tudo normal", "ocorrencia": ""},
            files={"foto": ("foto.png", _png_bytes(), "image/png")},
        )
        assert reading.status_code == 201
        assert reading.json()["ponto"]["codigo_qr"] == qr_code

        duplicate = client.post(
            "/ronda/leituras",
            headers=headers,
            data={"codigo_qr": qr_code, "observacao": "", "ocorrencia": ""},
            files={"foto": ("foto.png", _png_bytes(), "image/png")},
        )
        assert duplicate.status_code == 429
        assert "carencia" in duplicate.json()["detail"].lower()

        finished = client.post(
            "/ronda/turnos/finalizar",
            headers=headers,
            json={"observacao_final": "Teste finalizado"},
        )
        assert finished.status_code == 200
        body = finished.json()
        assert body["status"] == "finished"
        assert body["relatorio_html"].endswith(".html")


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
