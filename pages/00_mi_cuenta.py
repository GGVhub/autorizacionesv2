"""
00_mi_cuenta.py — Perfil del usuario y cambio de contraseña.
Acceso: todos los perfiles.
"""
import streamlit as st
from sqlalchemy import text
from datetime import timezone, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import require_login, get_connection, hash_password

require_login()

conn = get_connection()
ARG  = timezone(timedelta(hours=-3))

st.title("👤 Mi Cuenta")
st.caption("Información de tu perfil y configuración de contraseña.")

# ─── Datos del usuario ─────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")

df = conn.query(
    "SELECT * FROM usuarios WHERE id = :id",
    params={"id": user_id},
    ttl=0
)

if df.empty:
    st.error("No se encontró el usuario.")
    st.stop()

user = df.iloc[0]

PERFIL_LABELS = {
    1: "👑 Secretaria General",
    2: "✅ Autorizante Titular Serv. Administrativo",
    3: "📋 Administración",
    4: "📋 Compras",
    5: "✅ Autorizante por Secretaría",
    6: "📝 Requiriente",
}

try:
    ultimo = (
        __import__("pandas").to_datetime(user["ultimo_acceso"], utc=True)
        .tz_convert(ARG).strftime("%d/%m/%Y %H:%M")
    )
except:
    ultimo = "—"

# ─── Tarjeta de perfil ─────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📋 Datos del perfil")
    st.markdown(f"**Nombre:**  {user['nombre_apellido']}")
    st.markdown(f"**Usuario:** `{user['usuario']}`")
    st.markdown(f"**Perfil:**  {PERFIL_LABELS.get(int(user['profile']), str(user['profile']))}")
    st.markdown(f"**Secretaría:** {user['secretaria'] or '—'}")
    if user['sub_secretaria']:
        st.markdown(f"**Sub Secretaría:** {user['sub_secretaria']}")
    st.markdown(f"**Último acceso:** {ultimo}")

with col2:
    st.markdown("#### 🔐 Cambiar contraseña")

    with st.form("form_cambio_pass"):
        actual   = st.text_input("Contraseña actual", type="password")
        nueva1   = st.text_input("Nueva contraseña", type="password",
                                  help="Mínimo 6 caracteres")
        nueva2   = st.text_input("Repetir nueva contraseña", type="password")
        guardar  = st.form_submit_button("💾 Actualizar contraseña", type="primary", use_container_width=True)

    if guardar:
        if not actual or not nueva1 or not nueva2:
            st.error("Completá todos los campos.")
        elif hash_password(actual) != user["password_hash"]:
            st.error("❌ La contraseña actual es incorrecta.")
        elif len(nueva1) < 6:
            st.error("La nueva contraseña debe tener al menos 6 caracteres.")
        elif nueva1 != nueva2:
            st.error("Las contraseñas nuevas no coinciden.")
        elif nueva1 == actual:
            st.error("La nueva contraseña debe ser diferente a la actual.")
        else:
            try:
                with conn.session as session:
                    session.execute(
                        text("""UPDATE usuarios
                                SET password_hash = :h, debe_cambiar_pass = FALSE
                                WHERE id = :id"""),
                        {"h": hash_password(nueva1), "id": user_id}
                    )
                    session.commit()
                st.session_state.debe_cambiar_pass = False
                st.success("✅ Contraseña actualizada correctamente.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

st.divider()

# ─── Admin: gestión de usuarios ────────────────────────────────────────────
if st.session_state.get("user_profile") == 1:
    st.markdown("### 🛠️ Administración de usuarios")
    st.caption("Solo visible para el perfil Administrador.")

    df_users = conn.query(
        "SELECT id, nombre_apellido, usuario, profile, activo, debe_cambiar_pass, ultimo_acceso "
        "FROM usuarios ORDER BY nombre_apellido",
        ttl=0
    )

    df_users["ultimo_acceso"] = __import__("pandas").to_datetime(
        df_users["ultimo_acceso"], utc=True, errors="coerce"
    ).dt.tz_convert(ARG).dt.strftime("%d/%m/%Y %H:%M").fillna("Nunca")

    df_users["profile"] = df_users["profile"].map(lambda x: PERFIL_LABELS.get(int(x), str(x)))

    df_users.columns = ["ID", "Nombre", "Usuario", "Perfil", "Activo", "Debe cambiar pass", "Último acceso"]

    st.dataframe(df_users, use_container_width=True, hide_index=True)

    st.markdown("#### 🔑 Resetear contraseña de un usuario")
    col_r1, col_r2, col_r3 = st.columns([2, 2, 1])
    with col_r1:
        usuario_reset = st.text_input("Usuario a resetear", placeholder="nombre.apellido")
    with col_r2:
        nueva_pass_admin = st.text_input("Nueva contraseña", type="password", value="cambiar123")
    with col_r3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Resetear", type="primary"):
            if not usuario_reset.strip():
                st.warning("Ingresá el usuario.")
            else:
                check = conn.query(
                    "SELECT id FROM usuarios WHERE usuario = :u",
                    params={"u": usuario_reset.strip().lower()},
                    ttl=0
                )
                if check.empty:
                    st.error(f"Usuario '{usuario_reset}' no encontrado.")
                else:
                    with conn.session as session:
                        session.execute(
                            text("""UPDATE usuarios
                                    SET password_hash = :h, debe_cambiar_pass = TRUE
                                    WHERE usuario = :u"""),
                            {"h": hash_password(nueva_pass_admin), "u": usuario_reset.strip().lower()}
                        )
                        session.commit()
                    st.success(f"✅ Contraseña reseteada para **{usuario_reset}**. Deberá cambiarla al ingresar.")