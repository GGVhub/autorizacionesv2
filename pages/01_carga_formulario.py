"""
01_carga_formulario.py — Carga de nuevos formularios de gasto.
"""
import streamlit as st
from sqlalchemy import text
from datetime import datetime, timezone, timedelta, date
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import require_page_access, get_connection, fmt_currency

# ─── Clave para resetear el formulario ────────────────────────────────────
if "form_version" not in st.session_state:
    st.session_state.form_version = 0
if "formulario_guardado" not in st.session_state:
    st.session_state.formulario_guardado = False
require_page_access("formulario")

FECHA_LIMITE = datetime(2026, 6, 22, 23, 59, 0, tzinfo=timezone(timedelta(hours=-3)))
ahora = datetime.now(timezone(timedelta(hours=-3)))

if ahora > FECHA_LIMITE:
    st.error(f"🚫 La carga de formularios solo estaba habilitada hasta el **{FECHA_LIMITE.strftime('%d/%m/%Y a las %H:%M')} hs.**")
    st.stop()

st.title("📝 Carga de Formulario")
st.warning(f"⏰ Fecha límite de carga: **{FECHA_LIMITE.strftime('%d/%m/%Y a las %H:%M')} hs.**")


# Mostrar mensaje de éxito si viene de un submit exitoso
if "success_msg" in st.session_state and st.session_state.success_msg:
    st.success(st.session_state.success_msg)
    st.session_state.success_msg = ""
    st.balloons()

st.divider()
st.divider()

conn = get_connection()

user_id = st.session_state.get("user_id")
df_user = conn.query(
    "SELECT nombre_apellido, secretaria, sub_secretaria FROM usuarios WHERE id = :id",
    params={"id": user_id}, ttl=0
)

if df_user.empty:
    st.error("No se pudieron cargar los datos del usuario.")
    st.stop()

usuario_datos       = df_user.iloc[0]
secretaria_auto     = str(usuario_datos["secretaria"]     or "").strip()
sub_secretaria_auto = str(usuario_datos["sub_secretaria"] or "").strip()
nombre_auto         = str(usuario_datos["nombre_apellido"] or "").strip()

# ─── Datos del Solicitante ─────────────────────────────────────────────────
st.subheader("📌 Datos del Solicitante")
col1, col2, col3 = st.columns(3)
with col1:
    st.text_input("Nombre del Solicitante", value=nombre_auto, disabled=True)
with col2:
    st.text_input("Secretaría", value=secretaria_auto or "Sin secretaría asignada", disabled=True)
with col3:
    st.text_input("Sub Secretaría", value=sub_secretaria_auto or "—", disabled=True)

# ─── Detalle del Bien o Servicio ───────────────────────────────────────────
st.subheader("🛒 Detalle del Bien o Servicio")
col4, col5 = st.columns([2, 1])
with col4:
    bien_servicio = st.text_input(
    "Bien / Servicio *",
    placeholder="Ej: Resmas A4",
    key=f"bien_servicio_{st.session_state.form_version}"
    )
with col5:
    unidad_seleccion = st.selectbox(
    "Unidad de Medida *",
    options=["Unidad", "Kilo", "Litro", "Horas", "Dias", "Otro"],
    key=f"unidad_sel_{st.session_state.form_version}"
)

unidad_manual = ""
if unidad_seleccion == "Otro":
    unidad_manual = st.text_input(
        "✏️ Especificá la unidad de medida *",
        placeholder="Ej: Resma, Metro, Caja...",
        key=f"unidad_manual_{st.session_state.form_version}"
    )

unidad_medida = unidad_manual.strip() if unidad_seleccion == "Otro" else unidad_seleccion

col6, col7 = st.columns(2)
with col6:
    precio_unitario = st.number_input(
    "Precio Unitario ($) *",
    min_value=0.01, step=0.01, format="%.2f",
    key=f"precio_{st.session_state.form_version}"
    )
with col7:
    cantidad = st.number_input(
    "Cantidad *",
    min_value=1, step=1,
    key=f"cantidad_{st.session_state.form_version}"
    )

total_preview = precio_unitario * cantidad
st.info(f"💰 **Total estimado:** $ {total_preview:,.2f}")

# ─── Clasificación ─────────────────────────────────────────────────────────
st.subheader("📋 Clasificación")
col8, col9 = st.columns(2)
with col8:
    tipo_gasto = st.selectbox(
    "Tipo de Gasto *",
    options=["Esencial", "Serv. Basico", "Politica del gobernador"],
    key=f"tipo_gasto_{st.session_state.form_version}"
    )
with col9:
    prioridad = st.selectbox(
    "Prioridad *",
    options=["Alta", "Media", "Baja"],
    key=f"prioridad_{st.session_state.form_version}"
    )

gasto_escuelas = st.checkbox(
    "🏫 ¿Es gasto destinado a Escuelas?",
    key=f"escuelas_{st.session_state.form_version}"
)

# ─── Fecha ─────────────────────────────────────────────────────────────────
st.subheader("📅 Fecha del Requerimiento")
fecha_requerimiento = st.date_input(
    "Fecha límite del requerimiento (opcional)",
    value=None, min_value=date.today(), format="DD/MM/YYYY",
    key=f"fecha_{st.session_state.form_version}"
)

# ─── Justificación ─────────────────────────────────────────────────────────
st.subheader("📄 Justificación")
justificacion = st.text_area(
    "Justificación del gasto *", height=120,
    placeholder="Describe brevemente por qué se requiere este gasto...",
    key=f"justificacion_{st.session_state.form_version}"
)

st.divider()

# ─── Submit ────────────────────────────────────────────────────────────────
if st.button("💾 Registrar Solicitud", type="primary", use_container_width=True):
    errors = []
    if not nombre_auto:
        errors.append("No se pudo identificar el solicitante.")
    if not secretaria_auto:
        errors.append("Tu usuario no tiene secretaría asignada. Contactá al administrador.")
    if not bien_servicio.strip():
        errors.append("El bien/servicio es obligatorio.")
    if not unidad_medida:
        errors.append("La unidad de medida es obligatoria." if unidad_seleccion != "Otro" else "Especificá la unidad de medida.")
    if precio_unitario <= 0:
        errors.append("El precio unitario debe ser mayor a 0.")
    if cantidad <= 0:
        errors.append("La cantidad debe ser mayor a 0.")
    if len(justificacion.strip()) < 20:
        errors.append("La justificación debe tener al menos 20 caracteres.")

    if errors:
        for err in errors:
            st.error(f"⚠️ {err}")
    else:
        try:
            sql = text("""
                INSERT INTO formularios
                    (solicitante, secretaria, sub_secretaria,
                     bien_servicio, unidad_medida,
                     precio_unitario, cantidad, justificacion,
                     tipo_gasto, prioridad, gasto_escuelas,
                     fecha_requerimiento)
                VALUES
                    (:solicitante, :secretaria, :sub_secretaria,
                     :bien_servicio, :unidad_medida,
                     :precio_unitario, :cantidad, :justificacion,
                     :tipo_gasto, :prioridad, :gasto_escuelas,
                     :fecha_requerimiento)
                RETURNING id
            """)
            nuevo_id = None
            with conn.session as session:
                result = session.execute(sql, {
                    "solicitante":         nombre_auto,
                    "secretaria":          secretaria_auto,
                    "sub_secretaria":      sub_secretaria_auto or None,
                    "bien_servicio":       bien_servicio.strip(),
                    "unidad_medida":       unidad_medida,
                    "precio_unitario":     float(precio_unitario),
                    "cantidad":            int(cantidad),
                    "justificacion":       justificacion.strip(),
                    "tipo_gasto":          tipo_gasto,
                    "prioridad":           prioridad,
                    "gasto_escuelas":      bool(gasto_escuelas),
                    "fecha_requerimiento": fecha_requerimiento,
                })
                nuevo_id = result.fetchone()[0]
                session.commit()

            fecha_str = f" | Fecha requerida: **{fecha_requerimiento.strftime('%d/%m/%Y')}**" if fecha_requerimiento else ""
            st.success(
                f"✅ **Solicitud registrada exitosamente.**\n\n"
                f"ID: **#{nuevo_id}** | Solicitante: **{nombre_auto}** | "
                f"Secretaría: **{secretaria_auto}** | "
                f"Total: **$ {total_preview:,.2f}** | Prioridad: **{prioridad}**{fecha_str}"
            )
            st.balloons()
            st.session_state.formulario_guardado = True

        except Exception as e:
            st.error(f"❌ Error al guardar en la base de datos: {e}")

# ─── Botón para cargar nuevo formulario ───────────────────────────────────
if st.session_state.get("formulario_guardado"):
    if st.button("➕ Cargar nuevo formulario", type="secondary", use_container_width=True):
        st.session_state.form_version += 1
        st.session_state.formulario_guardado = False
        st.rerun()
# ─── Ayuda ─────────────────────────────────────────────────────────────────
with st.expander("ℹ️ Ayuda sobre los campos"):
    st.markdown("""
| Campo | Descripción |
|-------|-------------|
| **Secretaría / Sub Secretaría** | Se completan automáticamente con los datos de tu usuario |
| **Unidad de Medida** | Seleccioná de la lista o elegí "Otro" para ingresar una personalizada |
| **Tipo de Gasto** | *Esencial*: indispensable · *Serv. Basico*: servicios base · *Politica del gobernador*: lineamiento político |
| **Prioridad** | *Alta*: urgente/crítico · *Media*: necesario · *Baja*: puede esperar |
| **Fecha límite** | Opcional — dejá en blanco si no tiene fecha límite |
| **Total** | Se calcula automáticamente: Precio Unitario × Cantidad |
""")
