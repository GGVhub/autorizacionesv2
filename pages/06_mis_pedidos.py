"""
06_mis_pedidos.py — Mis pedidos: resumen y edición de formularios propios.
Acceso: Perfiles 1-6 (todos).
"""
import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import timezone, timedelta
from io import BytesIO
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import require_page_access, get_connection, fmt_currency

require_page_access("mis_pedidos")

st.title("📦 Mis Pedidos")
st.caption("Resumen y seguimiento de tus solicitudes de gasto.")

conn = get_connection()
ARG  = timezone(timedelta(hours=-3))

# ─── Nombre del usuario logueado ──────────────────────────────────────────
user_id = st.session_state.get("user_id")

df_user = conn.query(
    "SELECT nombre_apellido FROM usuarios WHERE id = :id",
    params={"id": user_id},
    ttl=0
)

if df_user.empty:
    st.error("No se pudieron cargar los datos del usuario.")
    st.stop()

nombre_usuario = str(df_user.iloc[0]["nombre_apellido"]).strip()

# ─── Cargar formularios del usuario ───────────────────────────────────────
def load_mis_formularios(nombre):
    return conn.query(
        """SELECT * FROM formularios
           WHERE solicitante = :n
             AND (autorizado1 IS NULL OR autorizado1 = FALSE)
             AND fecha_aut1 IS NULL
           ORDER BY created_at DESC""",
        params={"n": nombre},
        ttl=0
    )

try:
    df = load_mis_formularios(nombre_usuario)
except Exception as e:
    st.error(f"❌ Error de base de datos: {e}")
    st.stop()

if df.empty:
    st.info(f"👋 Hola **{nombre_usuario}**, no tenés formularios pendientes de autorización.")
    st.stop()

# ─── KPIs ──────────────────────────────────────────────────────────────────
total_monto = pd.to_numeric(df["total"], errors="coerce").sum()
aprobados   = df[df["autorizado2"] == True]
pendientes  = df[(df["autorizado1"] != True) & (df["autorizado2"] != True)]
en_revision = df[(df["autorizado1"] == True) & (df["autorizado2"] != True)]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📋 Mis formularios", len(df))
c2.metric("💰 Monto total",      fmt_currency(total_monto))
c3.metric("⏳ Pendientes",       len(pendientes))
#c4.metric("🔄 En revisión",      len(en_revision))
#c5.metric("✅ Aprobados",        len(aprobados))

st.divider()

# ─── IDs bloqueados (ya autorizados) ──────────────────────────────────────
ids_bloqueados = set(df[df["autorizado1"] == True]["id"].tolist())

# ─── Tabla editable ────────────────────────────────────────────────────────
st.subheader("📝 Detalle y edición")
st.caption("Solo podés editar formularios que aún no fueron autorizados (⏳ Pendiente).")

df_tabla = df[[
    "id", "bien_servicio", "unidad_medida",
    "precio_unitario", "cantidad", "total",
    "tipo_gasto", "prioridad", "gasto_escuelas",
    "fecha_requerimiento", "justificacion",
    "created_at"
]].copy()

df_tabla["total"]               = pd.to_numeric(df_tabla["total"], errors="coerce")
df_tabla["precio_unitario"]     = pd.to_numeric(df_tabla["precio_unitario"], errors="coerce")
df_tabla["fecha_requerimiento"] = pd.to_datetime(df_tabla["fecha_requerimiento"], errors="coerce").dt.date
df_tabla["created_at"]          = pd.to_datetime(df_tabla["created_at"], utc=True)\
                                   .dt.tz_convert(ARG).dt.strftime("%d/%m/%Y %H:%M")

df_tabla.columns = [
    "ID", "Bien/Servicio", "Unidad",
    "P. Unitario", "Cantidad", "Total",
    "Tipo Gasto", "Prioridad", "Escuelas",
    "Fecha Requerida", "Justificación",
    "Cargado"
]

edited_df = st.data_editor(
    df_tabla,
    use_container_width=True,
    hide_index=True,
    disabled=["ID", "Total", "Cargado"],
    column_config={
        "ID":              st.column_config.NumberColumn(width="small"),
        "Total":           st.column_config.NumberColumn(format="$ %.2f", disabled=True),
        "P. Unitario":     st.column_config.NumberColumn(format="$ %.2f", min_value=0.01),
        "Cantidad":        st.column_config.NumberColumn(min_value=1, step=1),
        "Tipo Gasto":      st.column_config.SelectboxColumn(
                               options=["Esencial", "Serv. Basico", "Politica del gobernador"]
                           ),
        "Prioridad":       st.column_config.SelectboxColumn(
                               options=["Alta", "Media", "Baja"]
                           ),
        "Unidad":          st.column_config.SelectboxColumn(
                               options=["Unidad", "Kilo", "Litro", "Horas", "Dias", "Otro"]
                           ),
        "Escuelas":        st.column_config.CheckboxColumn(),
        "Fecha Requerida": st.column_config.DateColumn(format="DD/MM/YYYY"),
        "Justificación":   st.column_config.TextColumn(width="large"),
    },
    key="tabla_mis_pedidos"
)

# ─── Guardar cambios ───────────────────────────────────────────────────────
if st.button("💾 Guardar cambios", type="primary"):
    cambios = 0
    try:
        with conn.session as session:
            for i, edit_row in edited_df.iterrows():
                fid = int(edit_row["ID"])

                if fid in ids_bloqueados:
                    continue

                orig = df_tabla.loc[i]
                campos = ["Bien/Servicio", "Unidad", "P. Unitario", "Cantidad",
                          "Tipo Gasto", "Prioridad", "Escuelas",
                          "Fecha Requerida", "Justificación"]

                hay_cambio = any(str(edit_row[c]) != str(orig[c]) for c in campos)

                if hay_cambio:
                    session.execute(text("""
                        UPDATE formularios SET
                            bien_servicio       = :bien_servicio,
                            unidad_medida       = :unidad_medida,
                            precio_unitario     = :precio_unitario,
                            cantidad            = :cantidad,
                            tipo_gasto          = :tipo_gasto,
                            prioridad           = :prioridad,
                            gasto_escuelas      = :gasto_escuelas,
                            fecha_requerimiento = :fecha_requerimiento,
                            justificacion       = :justificacion
                        WHERE id = :id
                    """), {
                        "bien_servicio":       str(edit_row["Bien/Servicio"]),
                        "unidad_medida":       str(edit_row["Unidad"]),
                        "precio_unitario":     float(edit_row["P. Unitario"]),
                        "cantidad":            int(edit_row["Cantidad"]),
                        "tipo_gasto":          str(edit_row["Tipo Gasto"]),
                        "prioridad":           str(edit_row["Prioridad"]),
                        "gasto_escuelas":      bool(edit_row["Escuelas"]),
                        "fecha_requerimiento": edit_row["Fecha Requerida"] if pd.notna(edit_row["Fecha Requerida"]) else None,
                        "justificacion":       str(edit_row["Justificación"]),
                        "id":                  fid,
                    })
                    cambios += 1

            session.commit()

        if cambios > 0:
            st.success(f"✅ {cambios} formulario(s) actualizado(s).")
            st.rerun()
        else:
            st.info("No se detectaron cambios.")

    except Exception as e:
        st.error(f"❌ Error al guardar: {e}")

if ids_bloqueados:
    st.caption(f"⚠️ Los formularios {sorted(ids_bloqueados)} ya tienen autorización y no pueden editarse.")

st.divider()

# ─── Exportar Excel ────────────────────────────────────────────────────────
st.subheader("⬇️ Exportar")

def generar_excel(dataframe):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Mis Pedidos")
        ws = writer.sheets["Mis Pedidos"]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col) + 4
            ws.column_dimensions[col[0].column_letter].width = min(max_len, 45)
    return output.getvalue()

st.download_button(
    label="📥 Exportar mis pedidos a Excel (.xlsx)",
    data=generar_excel(df_tabla),
    file_name=f"mis_pedidos_{nombre_usuario.replace(' ', '_')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)