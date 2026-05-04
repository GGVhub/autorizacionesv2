"""
03_autorizante1.py — Panel de autorización de primer nivel.
Acceso: Perfiles 1 y 2.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import require_page_access, get_connection, fmt_currency

require_page_access("autorizante1")

st.title("✅ Autorizante — Nivel 1")
st.caption("Gestiona las solicitudes pendientes de primera autorización.")

conn = get_connection()
ARG  = timezone(timedelta(hours=-3))

def load_pending():
    return conn.query(
        """SELECT * FROM formularios
           WHERE (autorizado1 IS NULL OR autorizado1 = FALSE)
             AND fecha_aut1 IS NULL
           ORDER BY
             CASE prioridad WHEN 'Alta' THEN 1 WHEN 'Media' THEN 2 ELSE 3 END,
             created_at ASC""",
        ttl=0
    )

try:
    df = load_pending()
except Exception as e:
    st.error(f"❌ Error de base de datos: {e}")
    st.stop()

# ─── KPIs ──────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("📋 Pendientes",      len(df))
c2.metric("💰 Monto Pendiente", fmt_currency(pd.to_numeric(df["total"], errors="coerce").sum()) if not df.empty else "$ 0,00")
alta = len(df[df["prioridad"] == "Alta"]) if not df.empty else 0
c3.metric("🔴 Alta Prioridad",  alta)

st.divider()

if df.empty:
    st.success("🎉 No hay formularios pendientes de autorización.")
    st.stop()

# ─── Filtros ───────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns(2)
with col_f1:
    filtro_prioridad = st.multiselect("Prioridad", ["Alta", "Media", "Baja"], default=["Alta", "Media", "Baja"])
with col_f2:
    filtro_area = st.multiselect("Secretaría", df["secretaria"].dropna().unique().tolist() if "secretaria" in df.columns else [])

df_show = df.copy()
if filtro_prioridad:
    df_show = df_show[df_show["prioridad"].isin(filtro_prioridad)]
if filtro_area and "secretaria" in df_show.columns:
    df_show = df_show[df_show["secretaria"].isin(filtro_area)]

st.subheader(f"📄 Solicitudes Pendientes ({len(df_show)})")

PRIORIDAD_COLORS = {"Alta": "🔴", "Media": "🟡", "Baja": "🟢"}

# ─── Loop de tarjetas ──────────────────────────────────────────────────────
for _, row in df_show.iterrows():
    fid = int(row["id"])

    try:
        created_str = pd.to_datetime(row["created_at"], utc=True).tz_convert(ARG).strftime("%d/%m/%Y %H:%M")
    except:
        created_str = "—"

    f_req_str = pd.to_datetime(row["fecha_requerimiento"]).strftime("%d/%m/%Y") \
                if pd.notna(row.get("fecha_requerimiento")) else "—"

    secretaria_str   = str(row.get("secretaria", "—")   or "—").strip()
    sub_sec_str      = str(row.get("sub_secretaria", "—") or "—").strip()

    with st.expander(
        f"#{fid} — {row['solicitante']} | {secretaria_str} | "
        f"{PRIORIDAD_COLORS.get(row['prioridad'], '')} {row['prioridad']} | "
        f"💰 {fmt_currency(row['total'])}",
        expanded=False,
    ):
        # ── Detalle ────────────────────────────────────────────────────────
        col_d1, col_d2, col_d3 = st.columns(3)
        col_d1.markdown(f"**Solicitante:** {row['solicitante']}")
        col_d1.markdown(f"**Secretaría:** {secretaria_str}")
        col_d1.markdown(f"**Sub Secretaría:** {sub_sec_str}")
        col_d2.markdown(f"**Bien/Servicio:** {row['bien_servicio']}")
        col_d2.markdown(f"**Unidad:** {row['unidad_medida']} × {row['cantidad']}")
        col_d2.markdown(f"**P. Unitario:** {fmt_currency(row['precio_unitario'])}")
        col_d3.markdown(f"**Total:** {fmt_currency(row['total'])}")
        col_d3.markdown(f"**Tipo Gasto:** {row['tipo_gasto']}")
        col_d3.markdown(f"**Escuelas:** {'✅' if row['gasto_escuelas'] else '❌'}")
        col_d3.markdown(f"**Fecha req.:** {f_req_str}")
        st.markdown(f"**Justificación:** {row['justificacion']}")
        st.caption(f"Cargado: {created_str}")

        st.markdown("---")

        # ── Botones principales ────────────────────────────────────────────
        btn1, btn2, btn3 = st.columns(3)
        with btn1:
            if st.button("✅ Autorizar", key=f"a1_si_{fid}", type="primary"):
                st.session_state[f"a1_confirm_{fid}"] = "autorizar"
                st.session_state.pop(f"a1_edit_{fid}", None)
        with btn2:
            if st.button("❌ Rechazar", key=f"a1_no_{fid}"):
                st.session_state[f"a1_confirm_{fid}"] = "rechazar"
                st.session_state.pop(f"a1_edit_{fid}", None)
        with btn3:
            edit_label = "🔒 Cerrar edición" if st.session_state.get(f"a1_edit_{fid}") else "✏️ Editar"
            if st.button(edit_label, key=f"a1_editbtn_{fid}"):
                st.session_state[f"a1_edit_{fid}"] = not st.session_state.get(f"a1_edit_{fid}", False)
                st.session_state.pop(f"a1_confirm_{fid}", None)

        # ── Confirmación ───────────────────────────────────────────────────
        if st.session_state.get(f"a1_confirm_{fid}"):
            action = st.session_state[f"a1_confirm_{fid}"]
            icon   = "✅" if action == "autorizar" else "❌"
            label  = "AUTORIZAR" if action == "autorizar" else "RECHAZAR"
            st.warning(f"{icon} ¿Confirmás **{label}** el formulario #{fid} — {row['solicitante']}?")

            cy, cn = st.columns(2)
            with cy:
                if st.button("Sí, confirmar", key=f"a1_cyes_{fid}", type="primary"):
                    nuevo_val = action == "autorizar"
                    try:
                        with conn.session as session:
                            session.execute(
                                text("UPDATE formularios SET autorizado1 = :val, fecha_aut1 = :now WHERE id = :id"),
                                {"val": nuevo_val, "now": datetime.now(timezone.utc), "id": fid}
                            )
                            session.commit()
                        st.session_state.pop(f"a1_confirm_{fid}", None)
                        st.session_state.pop(f"a1_edit_{fid}", None)
                        verb = "autorizado" if nuevo_val else "rechazado"
                        st.success(f"✅ Formulario #{fid} {verb}.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            with cn:
                if st.button("Cancelar", key=f"a1_cno_{fid}"):
                    st.session_state.pop(f"a1_confirm_{fid}", None)
                    st.rerun()

        # ── Panel de edición ───────────────────────────────────────────────
        if st.session_state.get(f"a1_edit_{fid}"):
            st.markdown("#### ✏️ Editar formulario")

            e1, e2 = st.columns(2)
            with e1:
                e_bien = st.text_input(
                    "Bien/Servicio",
                    value=str(row["bien_servicio"]),
                    key=f"a1_bien_{fid}"
                )
                opciones_unidad = ["Unidad", "Kilo", "Litro", "Horas", "Dias", "Otro"]
                idx_unidad = opciones_unidad.index(row["unidad_medida"]) \
                             if row["unidad_medida"] in opciones_unidad else 5
                e_unidad_sel = st.selectbox(
                    "Unidad de Medida",
                    options=opciones_unidad,
                    index=idx_unidad,
                    key=f"a1_unidad_{fid}"
                )
                e_unidad = st.text_input(
                    "Especificá la unidad",
                    value=str(row["unidad_medida"]),
                    key=f"a1_umanual_{fid}",
                    disabled=(e_unidad_sel != "Otro")
                )
                e_unidad_final = e_unidad.strip() if e_unidad_sel == "Otro" else e_unidad_sel

                e_precio = st.number_input(
                    "Precio Unitario",
                    value=float(row["precio_unitario"]),
                    min_value=0.01, format="%.2f",
                    key=f"a1_precio_{fid}"
                )
                e_cant = st.number_input(
                    "Cantidad",
                    value=int(row["cantidad"]),
                    min_value=1,
                    key=f"a1_cant_{fid}"
                )

            with e2:
                opciones_tipo = ["Esencial", "Serv. Basico", "Politica del gobernador"]
                idx_tipo = opciones_tipo.index(row["tipo_gasto"]) if row["tipo_gasto"] in opciones_tipo else 0
                e_tipo = st.selectbox(
                    "Tipo de Gasto",
                    options=opciones_tipo,
                    index=idx_tipo,
                    key=f"a1_tipo_{fid}"
                )
                opciones_prior = ["Alta", "Media", "Baja"]
                idx_prior = opciones_prior.index(row["prioridad"]) if row["prioridad"] in opciones_prior else 0
                e_prior = st.selectbox(
                    "Prioridad",
                    options=opciones_prior,
                    index=idx_prior,
                    key=f"a1_prior_{fid}"
                )
                e_escuelas = st.checkbox(
                    "Gasto Escuelas",
                    value=bool(row["gasto_escuelas"]),
                    key=f"a1_esc_{fid}"
                )
                f_req_val = pd.to_datetime(row["fecha_requerimiento"]).date() \
                            if pd.notna(row.get("fecha_requerimiento")) else None
                e_fecha = st.date_input(
                    "Fecha Requerida (opcional)",
                    value=f_req_val,
                    format="DD/MM/YYYY",
                    key=f"a1_fecha_{fid}"
                )

            e_just = st.text_area(
                "Justificación",
                value=str(row["justificacion"]),
                height=100,
                key=f"a1_just_{fid}"
            )

            st.info(f"💰 Nuevo total estimado: **$ {e_precio * e_cant:,.2f}**")

            if st.button("💾 Guardar cambios", key=f"a1_save_{fid}", type="primary"):
                try:
                    with conn.session as session:
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
                            "bien_servicio":       e_bien.strip(),
                            "unidad_medida":       e_unidad_final,
                            "precio_unitario":     float(e_precio),
                            "cantidad":            int(e_cant),
                            "tipo_gasto":          e_tipo,
                            "prioridad":           e_prior,
                            "gasto_escuelas":      bool(e_escuelas),
                            "fecha_requerimiento": e_fecha if pd.notna(e_fecha) else None,
                            "justificacion":       e_just.strip(),
                            "id":                  fid,
                        })
                        session.commit()
                    st.session_state[f"a1_edit_{fid}"] = False
                    st.success(f"✅ Formulario #{fid} actualizado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al guardar: {e}")

st.divider()
if st.button("🔄 Actualizar lista", use_container_width=True):
    st.rerun()

# ─── Historial ─────────────────────────────────────────────────────────────
with st.expander("📜 Historial — últimas autorizaciones"):
    df_hist = conn.query(
        """SELECT id, solicitante, secretaria, total, autorizado1, fecha_aut1
           FROM formularios WHERE fecha_aut1 IS NOT NULL
           ORDER BY fecha_aut1 DESC LIMIT 20""",
        ttl=0
    )
    if not df_hist.empty:
        df_hist["autorizado1"] = df_hist["autorizado1"].apply(lambda x: "✅ Autorizado" if x else "❌ Rechazado")
        df_hist["total"]       = pd.to_numeric(df_hist["total"], errors="coerce").apply(fmt_currency)
        df_hist["fecha_aut1"]  = pd.to_datetime(df_hist["fecha_aut1"], utc=True).dt.tz_convert(ARG).dt.strftime("%d/%m/%Y %H:%M")
        df_hist.columns = ["ID", "Solicitante", "Secretaría", "Total", "Estado", "Fecha"]
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
    else:
        st.info("Sin historial aún.")