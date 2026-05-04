"""
utils.py — Funciones de base de datos y utilidades compartidas.
"""
import hashlib
import streamlit as st
import pandas as pd
from datetime import datetime

# ─── Perfiles y accesos ────────────────────────────────────────────────────
PAGE_ACCESS = {
    1: ["formulario", "mis_pedidos", "dashboard", "autorizante_secretario", "autorizante1", "autorizante2", "notas_pedido", "pendientes"],
    2: ["formulario", "mis_pedidos", "dashboard", "autorizante1","pendientes", "notas_pedido"],
    3: ["formulario", "mis_pedidos",  "pendientes"],
    4: ["formulario", "mis_pedidos", "pendientes"],
    5: ["formulario", "mis_pedidos", "autorizante_secretario"],
    6: ["formulario", "mis_pedidos"],
}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def require_login():
    if not st.session_state.get("logged_in"):
        st.error("🔒 Debes iniciar sesión primero.")
        st.stop()

def require_page_access(page_slug: str):
    if not st.session_state.get("logged_in"):
        st.error("🔒 Sesión expirada. Volvé al inicio.")
        st.stop()

@st.cache_resource
def get_connection():
    try:
        return st.connection("postgres", type="sql")
    except Exception as e:
        st.error(f"❌ No se pudo conectar a la base de datos: {e}")
        st.stop()

def fmt_currency(val) -> str:
    try:
        return f"$ {float(val):,.2f}"
    except (TypeError, ValueError):
        return "$ 0,00"

def fmt_bool(val) -> str:
    return "✅" if val else "❌"

def badge_prioridad(val: str) -> str:
    colors = {"Alta": "🔴", "Media": "🟡", "Baja": "🟢"}
    return f"{colors.get(val, '⚪')} {val}"