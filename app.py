from __future__ import annotations

import os

import requests
import streamlit as st
from jose import jwt

API_URL = os.getenv("API_URL", "http://localhost:8000")
SECRET_KEY = os.getenv("API__SECRET_KEY", "change-me-in-production")

st.set_page_config(page_title="RAG Pipeline Demo", layout="wide")
st.title("RAG Pipeline Demo")


def _token(tenant_id: str) -> str:
    token: str = jwt.encode(
        {"sub": "demo-user", "tenant_id": tenant_id},
        SECRET_KEY,
        algorithm="HS256",
    )
    return token


with st.sidebar:
    st.header("Configuration")
    tenant_id = st.text_input("Tenant ID", value="acme")
    st.caption(f"API : {API_URL}")
    try:
        health = requests.get(f"{API_URL}/health", timeout=3).json()
        st.success(f"API {health.get('status', 'ok')} — v{health.get('version', '?')}")
    except Exception:
        st.error("API inaccessible")

st.header("Poser une question")

query = st.text_input("Question", placeholder="What is RAG?")

if st.button("Envoyer", disabled=not query):
    with st.spinner("Génération en cours…"):
        try:
            resp = requests.post(
                f"{API_URL}/api/v1/query/",
                json={"query": query},
                headers={"Authorization": f"Bearer {_token(tenant_id)}"},
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()

            st.subheader("Réponse")
            st.write(data["answer"])

            col1, col2, col3 = st.columns(3)
            col1.metric("Latence", f"{data['latency_ms']:.0f} ms")
            col2.metric("Sources", len(data["sources"]))
            col3.metric("Cache", "✓" if data["cached"] else "✗")

            if data["sources"]:
                with st.expander("Sources"):
                    for s in data["sources"]:
                        st.markdown(f"**{s['source']}**")
                        st.caption(s["content"])
                        st.divider()
        except requests.HTTPError as e:
            st.error(f"Erreur {e.response.status_code} : {e.response.text}")
        except Exception as e:
            st.error(f"Erreur : {e}")
