import os

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Supervisao de Zeladoria", layout="wide")

st.title("Supervisao de Zeladoria")
st.caption("Painel operacional para facilities, conservacao e limpeza externa.")


def api_get(path: str, token: str):
    try:
        response = requests.get(
            f"{API_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"Nao foi possivel conectar na API em {API_BASE_URL}.")
        st.info("Abra outro terminal e rode: python -m uvicorn backend.app.main:app --reload")
        st.stop()


def api_post(path: str, token: str, payload: dict | None = None):
    try:
        response = requests.post(
            f"{API_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            json=payload or {},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        st.error(f"Nao foi possivel conectar na API em {API_BASE_URL}.")
        st.info("Abra outro terminal e rode: python -m uvicorn backend.app.main:app --reload")
        st.stop()


with st.sidebar:
    st.header("Acesso")
    email = st.text_input("Email", value="admin@facilities.local")
    password = st.text_input("Senha", value="admin123", type="password")
    if st.button("Entrar", use_container_width=True):
        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/login",
                data={"username": email, "password": password},
                timeout=15,
            )
            if response.ok:
                st.session_state["token"] = response.json()["access_token"]
                st.success("Login realizado.")
            else:
                st.error("Email ou senha invalidos.")
        except requests.RequestException:
            st.error(f"Nao foi possivel conectar na API em {API_BASE_URL}.")
            st.info("Abra outro terminal e rode: python -m uvicorn backend.app.main:app --reload")

token = st.session_state.get("token")
if not token:
    st.info("Entre com um usuario supervisor ou administrador.")
    st.stop()

metrics = api_get("/dashboard/metrics", token)
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Servicos realizados", metrics["services_done"])
col2.metric("Funcionarios ativos", metrics["active_employees"])
col3.metric("Ocorrencias abertas", metrics["open_occurrences"])
col4.metric("Faltas", metrics["absences"])
col5.metric("Fotos enviadas", metrics["photos_uploaded"])

tab_prod, tab_occ, tab_reports = st.tabs(["Produtividade", "Ocorrencias por local", "Relatorios"])

with tab_prod:
    productivity = api_get("/dashboard/productivity", token)
    st.subheader("Ranking de produtividade")
    st.dataframe(productivity, use_container_width=True, hide_index=True)
    if productivity:
        st.bar_chart(
            {item["employee_name"]: item["completed_services"] for item in productivity}
        )

with tab_occ:
    occurrences = api_get("/dashboard/occurrences-by-location", token)
    st.subheader("Ocorrencias por local")
    st.dataframe(occurrences, use_container_width=True, hide_index=True)
    if occurrences:
        st.bar_chart({item["location_name"]: item["total"] for item in occurrences})

with tab_reports:
    st.subheader("Relatorios em PDF")
    title = st.text_input("Titulo do relatorio", value="Relatorio de produtividade")
    if st.button("Gerar PDF"):
        report = api_post("/reports", token, {"report_type": "productivity", "title": title})
        st.success("Relatorio gerado.")
        st.link_button("Abrir PDF", f"{API_BASE_URL}{report['file_url']}")

    reports = api_get("/reports", token)
    st.dataframe(reports, use_container_width=True, hide_index=True)
