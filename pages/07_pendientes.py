"""
07_pendientes.py — Formularios pendientes de autorización secretario.
Acceso: Perfiles 3 y 4. Pueden editar formularios no autorizados.
"""
import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import timezone, timedelta, date
from io import BytesIO
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import require_page_access, get_connection, fmt_currency

require_page_access("pendientes")

st.title("📋 Formularios Pendientes")
st.caption("Formularios que aún no tienen autorización del Secretario.")

conn = get_connection()
ARG  = timezone(timedelta(hours=-3))

def load_pendientes():
    return conn.query(
        """SELECT id, solicitante, secretaria, sub_secretaria,
                  bien_servicio, unidad_medida, cantidad,
                  precio_unitario, total, tipo_gasto, prioridad,
                  gasto_escuelas, fecha_requerimiento, justificacion,
                  created_at
           FROM formularios
           WHERE (autorizado1 IS NULL OR autorizado1 = FALSE)
             AND fecha_aut1 IS NULL
           ORDER BY
             CASE prioridad WHEN 'Alta' THEN 1 WHEN 'Media' THEN 2 ELSE 3 END,
             created_at ASC""",
        ttl=0
    )

try:
    df = load_pendientes()
except Exception as e:
    st.error(f"❌ Error de base de datos: {e}")
    st.stop()

# ─── KPIs ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("📋 Total pendientes", len(df))
monto = pd.to_numeric(df["total"], errors="coerce").sum() if not df.empty else 0
c2.metric("💰 Monto total",       fmt_currency(monto))
alta  = len(df[df["prioridad"] == "Alta"]) if not df.empty else 0
c3.metric("🔴 Alta prioridad",    alta)
secs  = df["secretaria"].nunique() if not df.empty else 0
c4.metric("🏛️ Secretarías",       secs)

st.divider()

if df.empty:
    st.success("🎉 No hay formularios pendientes de autorización.")
    st.stop()

# ─── Filtros ───────────────────────────────────────────────────────────────
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    filtro_sec = st.multiselect("Secretaría", df["secretaria"].dropna().unique().tolist())
with col_f2:
    filtro_prioridad = st.multiselect("Prioridad", ["Alta", "Media", "Baja"])
with col_f3:
    filtro_tipo = st.multiselect("Tipo de Gasto", df["tipo_gasto"].dropna().unique().tolist())

df_show = df.copy()
if filtro_sec:
    df_show = df_show[df_show["secretaria"].isin(filtro_sec)]
if filtro_prioridad:
    df_show = df_show[df_show["prioridad"].isin(filtro_prioridad)]
if filtro_tipo:
    df_show = df_show[df_show["tipo_gasto"].isin(filtro_tipo)]

st.subheader(f"📄 {len(df_show)} formulario(s) pendientes")

# ─── Tabla editable ────────────────────────────────────────────────────────
df_edit = df_show.copy()
df_edit["total"]               = pd.to_numeric(df_edit["total"], errors="coerce")
df_edit["precio_unitario"]     = pd.to_numeric(df_edit["precio_unitario"], errors="coerce")
df_edit["fecha_requerimiento"] = pd.to_datetime(df_edit["fecha_requerimiento"], errors="coerce").dt.date
df_edit["created_at"]          = pd.to_datetime(df_edit["created_at"], utc=True)\
                                   .dt.tz_convert(ARG).dt.strftime("%d/%m/%Y %H:%M")

# Columnas que NO se pueden editar
cols_disabled = [
    "id", "solicitante", "secretaria", "sub_secretaria",
    "total", "created_at"
]

df_edit.columns = [
    "ID", "Solicitante", "Secretaría", "Sub Secretaría",
    "Bien/Servicio", "Unidad", "Cantidad",
    "P. Unitario", "Total", "Tipo Gasto", "Prioridad",
    "Escuelas", "Fecha Requerida", "Justificación", "Cargado"
]

cols_disabled_display = ["ID", "Solicitante", "Secretaría", "Sub Secretaría", "Total", "Cargado"]

edited_df = st.data_editor(
    df_edit,
    use_container_width=True,
    hide_index=True,
    disabled=cols_disabled_display,
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
    key="tabla_pendientes"
)

# ─── Botón guardar cambios ─────────────────────────────────────────────────
col_g1, col_g2 = st.columns([3, 1])
with col_g1:
    st.markdown(f"**💰 Monto total filtrado: {fmt_currency(pd.to_numeric(df_show['total'], errors='coerce').sum())}**")
with col_g2:
    if st.button("💾 Guardar cambios", type="primary", use_container_width=True):
        cambios = 0
        errores = []
        try:
            with conn.session as session:
                for i, edit_row in edited_df.iterrows():
                    orig = df_edit.loc[i]
                    fid  = int(edit_row["ID"])

                    # Detectar si hay cambios
                    campos_a_comparar = [
                        "Bien/Servicio", "Unidad", "Cantidad", "P. Unitario",
                        "Tipo Gasto", "Prioridad", "Escuelas",
                        "Fecha Requerida", "Justificación"
                    ]
                    hay_cambio = any(
                        str(edit_row[c]) != str(orig[c])
                        for c in campos_a_comparar
                    )

                    if hay_cambio:
                        session.execute(text("""
                            UPDATE formularios SET
                                bien_servicio       = :bien_servicio,
                                unidad_medida       = :unidad_medida,
                                cantidad            = :cantidad,
                                precio_unitario     = :precio_unitario,
                                tipo_gasto          = :tipo_gasto,
                                prioridad           = :prioridad,
                                gasto_escuelas      = :gasto_escuelas,
                                fecha_requerimiento = :fecha_requerimiento,
                                justificacion       = :justificacion
                            WHERE id = :id
                        """), {
                            "bien_servicio":       str(edit_row["Bien/Servicio"]),
                            "unidad_medida":       str(edit_row["Unidad"]),
                            "cantidad":            int(edit_row["Cantidad"]),
                            "precio_unitario":     float(edit_row["P. Unitario"]),
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
                st.success(f"✅ {cambios} formulario(s) actualizado(s) correctamente.")
                st.rerun()
            else:
                st.info("No se detectaron cambios.")

        except Exception as e:
            st.error(f"❌ Error al guardar: {e}")

st.divider()

# ─── Exportar ──────────────────────────────────────────────────────────────
def generar_excel(dataframe):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Pendientes")
        ws = writer.sheets["Pendientes"]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col) + 4
            ws.column_dimensions[col[0].column_letter].width = min(max_len, 45)
    return output.getvalue()

col_e1, col_e2 = st.columns(2)
with col_e1:
    st.download_button(
        label="📥 Exportar a Excel (.xlsx)",
        data=generar_excel(df_edit),
        file_name="formularios_pendientes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
with col_e2:
    if st.button("🔄 Actualizar", use_container_width=True):
        st.rerun()