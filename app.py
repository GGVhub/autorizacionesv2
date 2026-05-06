import streamlit as st
import os
from sqlalchemy import text

st.set_page_config(
    page_title="Sistema de Autorizaciones",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils import hash_password, get_connection, PAGE_ACCESS

# ─── Inicializar session_state ─────────────────────────────────────────────
for key, default in [
    ("logged_in",           False),
    ("user_email",          ""),
    ("user_profile",        None),
    ("user_name",           ""),
    ("user_usuario",        ""),
    ("user_id",             None),
    ("debe_cambiar_pass",   False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

st.markdown("""
<style>
    .stButton>button { border-radius: 8px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ─── Función de login contra BD ───────────────────────────────────────────
def verificar_credenciales(usuario: str, password: str):
    conn = get_connection()
    hashed = hash_password(password)
    df = conn.query(
        "SELECT id, nombre_apellido, usuario, profile, debe_cambiar_pass, activo "
        "FROM usuarios WHERE usuario = :u AND password_hash = :p",
        params={"u": usuario.strip().lower(), "p": hashed},
        ttl=0
    )
    if df.empty:
        return None
    row = df.iloc[0]
    if not row["activo"]:
        return None
    return row

def registrar_acceso(user_id: int):
    conn = get_connection()
    with conn.session as session:
        session.execute(
            text("UPDATE usuarios SET ultimo_acceso = NOW() WHERE id = :id"),
            {"id": user_id}
        )
        session.commit()

# ─── Página de login ───────────────────────────────────────────────────────
def login_page():
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown("## 📋 Sistema de Autorizaciones")
        st.markdown("Ingresá tu usuario y contraseña para continuar.")
        st.divider()

        with st.form("login_form"):
            usuario  = st.text_input("👤 Usuario", placeholder="nombre.apellido")
            password = st.text_input("🔒 Contraseña", type="password")
            submitted = st.form_submit_button("Ingresar", use_container_width=True, type="primary")

        if submitted:
            if not usuario or not password:
                st.error("Completá todos los campos.")
            else:
                user = verificar_credenciales(usuario, password)
                if user is not None:
                    st.session_state.logged_in          = True
                    st.session_state.user_id            = int(user["id"])
                    st.session_state.user_name          = user["nombre_apellido"]
                    st.session_state.user_usuario       = user["usuario"]
                    st.session_state.user_profile       = int(user["profile"])
                    st.session_state.debe_cambiar_pass  = bool(user["debe_cambiar_pass"])
                    registrar_acceso(int(user["id"]))
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")

        st.caption("🔑 Contraseña default: **cambiar123** — deberás cambiarla en tu primer ingreso.")

# ─── Si NO está logueado ───────────────────────────────────────────────────
if not st.session_state.logged_in:
    login_page()
    st.stop()

# ─── Si debe cambiar contraseña — forzar antes de continuar ───────────────
if st.session_state.debe_cambiar_pass:
    st.warning("⚠️ Debés cambiar tu contraseña antes de continuar.")
    st.markdown("### 🔐 Cambio de contraseña obligatorio")

    conn = get_connection()
    with st.form("form_cambio_obligatorio"):
        nueva1 = st.text_input("Nueva contraseña", type="password")
        nueva2 = st.text_input("Repetir nueva contraseña", type="password")
        ok = st.form_submit_button("Guardar contraseña", type="primary")

    if ok:
        if len(nueva1) < 6:
            st.error("La contraseña debe tener al menos 6 caracteres.")
        elif nueva1 != nueva2:
            st.error("Las contraseñas no coinciden.")
        else:
            with conn.session as session:
                session.execute(
                    text("UPDATE usuarios SET password_hash = :h, debe_cambiar_pass = FALSE WHERE id = :id"),
                    {"h": hash_password(nueva1), "id": st.session_state.user_id}
                )
                session.commit()
            st.session_state.debe_cambiar_pass = False
            st.success("✅ Contraseña actualizada. Continuando...")
            st.rerun()
    st.stop()

# ─── Navegación ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
profile  = st.session_state.user_profile

pg_mi_cuenta      = st.Page(os.path.join(BASE_DIR, "pages", "00_mi_cuenta.py"),                  title="👤 Mi Cuenta")
pg_formulario     = st.Page(os.path.join(BASE_DIR, "pages", "01_carga_formulario.py"),            title="📝 Carga Formulario")
pg_mis_pedidos    = st.Page(os.path.join(BASE_DIR, "pages", "06_mis_pedidos.py"),                 title="📦 Mis Pedidos")
pg_dashboard      = st.Page(os.path.join(BASE_DIR, "pages", "02_dashboard.py"),                   title="📊 Dashboard")
pg_pendientes     = st.Page(os.path.join(BASE_DIR, "pages", "07_pendientes.py"),                  title="📋 Pendientes")
pg_aut_secretario = st.Page(os.path.join(BASE_DIR, "pages", "03b_autorizante_secretario.py"),     title="✅ Aut. Secretario")
pg_autorizante1   = st.Page(os.path.join(BASE_DIR, "pages", "03_autorizante1.py"),                title="✅ Autorizante Titular Serv. Administrativo")
pg_autorizante2   = st.Page(os.path.join(BASE_DIR, "pages", "04_autorizante2.py"),                title="🔐 Autorizante Secretaria General")
pg_notas          = st.Page(os.path.join(BASE_DIR, "pages", "05_notas_de_pedido.py"),             title="🧾 Notas de Pedido")

PAGES_BY_PROFILE = {
    1: [pg_mi_cuenta, pg_formulario, pg_mis_pedidos, pg_dashboard, pg_aut_secretario, pg_autorizante1, pg_autorizante2, pg_notas],
    2: [pg_mi_cuenta, pg_formulario, pg_mis_pedidos, pg_dashboard, pg_autorizante1, pg_pendientes, pg_notas],
    3: [pg_mi_cuenta, pg_formulario, pg_mis_pedidos, pg_pendientes, pg_notas],
    4: [pg_mi_cuenta, pg_formulario, pg_mis_pedidos, pg_pendientes, pg_notas],
    5: [pg_mi_cuenta, pg_formulario, pg_mis_pedidos, pg_aut_secretario],
    6: [pg_mi_cuenta, pg_formulario, pg_mis_pedidos],
}

pages = PAGES_BY_PROFILE.get(profile, [pg_mi_cuenta, pg_formulario])

with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user_name}")
    st.caption(f"@{st.session_state.user_usuario}")
    st.caption(f"Perfil {profile}")
    st.divider()
    if st.button("🚪 Cerrar sesión", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

nav = st.navigation(pages)
nav.run()
