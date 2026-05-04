"""
04_autorizante2.py — Panel de autorización de segundo nivel (final).
Acceso: Solo Perfil 1 (Administrador).
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import require_page_access, get_connection, fmt_currency

require_page_access("autorizante2")

st.title("🔐 Autorizante — Nivel 2 (Final)")
st.caption("Gestiona las solicitudes que ya tienen autorización de nivel 1 y esperan aprobación final.")

conn = get_connection()

# ─── Cargar pendientes nivel 2 ─────────────────────────────────────────────
def load_pending_level2():
    return conn.query(
        """SELECT * FROM formularios
           WHERE autorizado1 = TRUE
             AND (autorizado2 IS NULL OR autorizado2 = FALSE)
             AND fecha_aut2 IS NULL
           ORDER BY prioridad, fecha_aut1""",
        ttl=0
    )

try:
    df = load_pending_level2()
except Exception as e:
    st.error(f"❌ Error de base de datos: {e}")
    st.stop()

# ─── KPIs ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
total_monto = pd.to_numeric(df["total"], errors="coerce").sum() if not df.empty else 0
c1.metric("📋 Pendientes Nivel 2",    len(df))
c2.metric("💰 Monto a Aprobar",        fmt_currency(total_monto))
alta = len(df[df["prioridad"] == "Alta"]) if not df.empty else 0
c3.metric("🔴 Alta Prioridad",         alta)

# Monto ya aprobado finalmente
df_aprobados = conn.query(
    "SELECT SUM(total) as total FROM formularios WHERE autorizado2 = TRUE", ttl=0
)
monto_aprobado = float(df_aprobados.iloc[0]["total"] or 0) if not df_aprobados.empty else 0
c4.metric("✅ Monto Aprobado Final",   fmt_currency(monto_aprobado))

st.divider()

if df.empty:
    st.success("🎉 ¡No hay formularios pendientes de autorización final!")

    with st.expander("📊 Resumen de aprobaciones finales"):
        df_final = conn.query(
            "SELECT id, solicitante, area, total, fecha_aut2 "
            "FROM formularios WHERE autorizado2 = TRUE ORDER BY fecha_aut2 DESC LIMIT 30",
            ttl=0
        )
        if not df_final.empty:
            df_final["total"]      = pd.to_numeric(df_final["total"], errors="coerce").apply(fmt_currency)
            df_final["fecha_aut2"] = pd.to_datetime(df_final["fecha_aut2"]).dt.strftime("%d/%m/%Y %H:%M")
            df_final.columns = ["ID", "Solicitante", "Área", "Total", "Fecha Aprobación"]
            st.dataframe(df_final, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no hay aprobaciones finales.")
    st.stop()

# ─── Filtros ───────────────────────────────────────────────────────────────
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    prioridad_filter = st.multiselect(
        "Prioridad", ["Alta", "Media", "Baja"], default=["Alta", "Media", "Baja"]
    )
with col_f2:
    area_filter = st.multiselect("Área", df["area"].dropna().unique().tolist())
with col_f3:
    escuelas_filter = st.selectbox("Gasto Escuelas", ["Todos", "Sí", "No"])

df_show = df.copy()
if prioridad_filter:
    df_show = df_show[df_show["prioridad"].isin(prioridad_filter)]
if area_filter:
    df_show = df_show[df_show["area"].isin(area_filter)]
if escuelas_filter == "Sí":
    df_show = df_show[df_show["gasto_escuelas"] == True]
elif escuelas_filter == "No":
    df_show = df_show[df_show["gasto_escuelas"] != True]

st.subheader(f"📄 Solicitudes en Espera de Aprobación Final ({len(df_show)})")

PRIORIDAD_COLORS = {"Alta": "🔴", "Media": "🟡", "Baja": "🟢"}

# ─── Cards por formulario ──────────────────────────────────────────────────
for _, row in df_show.iterrows():
    fid = int(row["id"])

    fecha_aut1_str = pd.to_datetime(row["fecha_aut1"]).strftime("%d/%m/%Y %H:%M") \
        if pd.notna(row["fecha_aut1"]) else "—"
    created_str = pd.to_datetime(row["created_at"]).strftime("%d/%m/%Y %H:%M") \
        if pd.notna(row["created_at"]) else "—"

    with st.expander(
        f"#{fid} — {row['solicitante']} | {row['area']} | "
        f"{PRIORIDAD_COLORS.get(row['prioridad'],'')} {row['prioridad']} | "
        f"💰 {fmt_currency(row['total'])} | ✅ Aut.1: {fecha_aut1_str}",
        expanded=False,
    ):
        col_d1, col_d2, col_d3 = st.columns(3)
        col_d1.markdown(f"**Bien/Servicio:** {row['bien_servicio']}")
        col_d1.markdown(f"**Unidad:** {row['unidad_medida']} × {row['cantidad']}")
        col_d2.markdown(f"**Precio Unit.:** {fmt_currency(row['precio_unitario'])}")
        col_d2.markdown(f"**Total:** {fmt_currency(row['total'])}")
        col_d3.markdown(f"**Tipo Gasto:** {row['tipo_gasto']}")
        col_d3.markdown(f"**Escuelas:** {'✅' if row['gasto_escuelas'] else '❌'}")

        st.markdown(f"**Justificación:** {row['justificacion']}")

        st.markdown("---")
        t1, t2 = st.columns(2)
        t1.markdown(f"📅 *Cargado:* {created_str}")
        t2.markdown(f"✅ *Aut. Nivel 1:* {fecha_aut1_str}")

        st.markdown("---")
        btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 4])

        with btn_col1:
            if st.button("🔐 Aprobar Final", key=f"aut2_si_{fid}", type="primary"):
                st.session_state[f"confirm_aut2_{fid}"] = "aprobar"

        with btn_col2:
            if st.button("❌ Rechazar", key=f"aut2_no_{fid}"):
                st.session_state[f"confirm_aut2_{fid}"] = "rechazar"

        # Confirmación
        if st.session_state.get(f"confirm_aut2_{fid}"):
            action = st.session_state[f"confirm_aut2_{fid}"]
            action_label = "APROBAR DEFINITIVAMENTE" if action == "aprobar" else "RECHAZAR"
            icon = "🔐" if action == "aprobar" else "❌"
            st.warning(f"{icon} ¿Confirmas **{action_label}** el formulario #{fid} — {row['solicitante']}?")
            if action == "aprobar":
                st.info(f"Esto aprobará definitivamente **{fmt_currency(row['total'])}** para **{row['bien_servicio']}**.")

            c_yes, c_no = st.columns(2)
            with c_yes:
                if st.button("Sí, confirmar", key=f"conf_yes_aut2_{fid}", type="primary"):
                    nuevo_val = True if action == "aprobar" else False
                    try:
                        sql = text("""
                            UPDATE formularios
                            SET autorizado2 = :val, fecha_aut2 = :now
                            WHERE id = :id
                        """)
                        with conn.session as session:
                            session.execute(sql, {
                                "val": nuevo_val,
                                "now": datetime.now(),
                                "id":  fid,
                            })
                            session.commit()
                        del st.session_state[f"confirm_aut2_{fid}"]
                        verb = "aprobado definitivamente" if nuevo_val else "rechazado"
                        st.success(f"✅ Formulario #{fid} {verb}.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar: {e}")

            with c_no:
                if st.button("Cancelar", key=f"conf_no_aut2_{fid}"):
                    del st.session_state[f"confirm_aut2_{fid}"]
                    st.rerun()

st.divider()
if st.button("🔄 Actualizar lista", use_container_width=True):
    st.rerun()

# ─── Historial aprobaciones finales ───────────────────────────────────────
with st.expander("📜 Historial — Aprobaciones finales recientes"):
    df_hist2 = conn.query(
        """SELECT id, solicitante, area, bien_servicio, total, autorizado2, fecha_aut2
           FROM formularios WHERE fecha_aut2 IS NOT NULL
           ORDER BY fecha_aut2 DESC LIMIT 20""",
        ttl=0
    )
    if not df_hist2.empty:
        df_hist2["autorizado2"] = df_hist2["autorizado2"].apply(
            lambda x: "✅ Aprobado" if x else "❌ Rechazado"
        )
        df_hist2["total"]       = pd.to_numeric(df_hist2["total"], errors="coerce").apply(fmt_currency)
        df_hist2["fecha_aut2"]  = pd.to_datetime(df_hist2["fecha_aut2"]).dt.strftime("%d/%m/%Y %H:%M")
        df_hist2.columns = ["ID", "Solicitante", "Área", "Bien/Servicio", "Total", "Estado Final", "Fecha"]
        st.dataframe(df_hist2, use_container_width=True, hide_index=True)
    else:
        st.info("Sin historial de aprobaciones finales.")
