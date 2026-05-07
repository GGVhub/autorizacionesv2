"""
05_notas_de_pedido.py — Notas de pedido (formularios con doble autorización).
Acceso: Perfiles 1 y 2.
"""
import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import timezone, timedelta, datetime
from io import BytesIO
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import require_page_access, get_connection, fmt_currency
from sqlalchemy import text

require_page_access("notas_pedido")



st.title("🧾 Notas de Pedido")
st.caption("Formularios con doble autorización aprobada, listos para emitir nota de pedido.")

conn = get_connection()
ARG  = timezone(timedelta(hours=-3))




def load_data():
    return conn.query(
        """SELECT * FROM formularios
           WHERE autorizado1 = TRUE AND autorizado2 = TRUE
           ORDER BY fecha_aut2 DESC""",
        ttl=0
    )

try:
    df = load_data()
except Exception as e:
    st.error(f"❌ Error de base de datos: {e}")
    st.stop()



# ─── Separar en dos grupos ─────────────────────────────────────────────────
def es_nota_vacia(val):
    if val is None:
        return True
    return str(val).strip().lower() in ("", "nan", "none", "null")

df["nota_de_pedido"] = df["nota_de_pedido"].apply(
    lambda x: "" if es_nota_vacia(x) else str(x).strip()
)

df_sin_nota = df[df["nota_de_pedido"] == ""].copy()
df_con_nota = df[df["nota_de_pedido"] != ""].copy()

# ─── KPIs ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("✅ Total aprobados",      len(df))
c2.metric("💰 Monto total",          fmt_currency(pd.to_numeric(df["total"], errors="coerce").sum()))
c3.metric("🧾 Con nota asignada",    len(df_con_nota))
c4.metric("⏳ Pendientes de nota",   len(df_sin_nota))

st.divider()

# ─── CSS tarjetas ──────────────────────────────────────────────────────────
st.markdown("""
<style>
.ticket {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-left: 5px solid #f59e0b;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.ticket-header {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1a3a5c;
    margin-bottom: 10px;
}
.ticket-footer {
    margin-top: 10px;
    font-size: 0.8rem;
    color: #6b7280;
    border-top: 1px dashed #d1d5db;
    padding-top: 8px;
}
</style>
""", unsafe_allow_html=True)

PRIORIDAD_COLORS = {"Alta": "🔴", "Media": "🟡", "Baja": "🟢"}

def fmt_fecha(val):
    try:
        return pd.to_datetime(val, utc=True).tz_convert(ARG).strftime("%d/%m/%Y %H:%M")
    except:
        return "—"

# ══════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — TICKETS SIN NOTA
# ══════════════════════════════════════════════════════════════════════════
st.subheader(f"⏳ Pendientes de asignar nota ({len(df_sin_nota)})")

if df_sin_nota.empty:
    st.success("🎉 Todos los formularios ya tienen nota de pedido asignada.")
else:
    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_area = st.multiselect("Filtrar por área", df_sin_nota["area"].dropna().unique().tolist())
    with col_f2:
        filtro_prioridad = st.multiselect("Filtrar por prioridad", ["Alta", "Media", "Baja"])

    df_show = df_sin_nota.copy()
    if filtro_area:
        df_show = df_show[df_show["area"].isin(filtro_area)]
    if filtro_prioridad:
        df_show = df_show[df_show["prioridad"].isin(filtro_prioridad)]

    for _, row in df_show.iterrows():
        fid = int(row["id"])

        created_str = fmt_fecha(row["created_at"])
        f_aut1_str  = fmt_fecha(row["fecha_aut1"])
        f_aut2_str  = fmt_fecha(row["fecha_aut2"])
        f_req_str   = pd.to_datetime(row["fecha_requerimiento"]).strftime("%d/%m/%Y") \
                      if pd.notna(row.get("fecha_requerimiento")) else "—"

        ticket_texto = f"""NOTA DE PEDIDO: (sin asignar)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ID FORMULARIO   : #{fid:<15}  ÁREA            : {row['area']}
SOLICITANTE     : {row['solicitante']:<15}  TIPO DE GASTO   : {row['tipo_gasto']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BIEN/SERVICIO   : {row['bien_servicio']:<15}  PRIORIDAD       : {PRIORIDAD_COLORS.get(row['prioridad'],'')} {row['prioridad']}
UNIDAD          : {str(row['unidad_medida']):<15}  GASTO ESCUELAS  : {'Sí' if row['gasto_escuelas'] else 'No'}
CANTIDAD        : {str(row['cantidad']):<15}  FECHA REQUERIDA : {f_req_str}
PRECIO UNITARIO : {fmt_currency(row['precio_unitario']):<15}  CARGADO         : {created_str}
TOTAL           : {fmt_currency(row['total']):<15}  AUTORIZACIÓN 1  : {f_aut1_str}
                                             AUTORIZACIÓN 2  : {f_aut2_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JUSTIFICACIÓN   : {row['justificacion']}"""

        st.markdown(f"""
<div class="ticket">
    <div class="ticket-header">
        ⏳ Sin nota &nbsp;|&nbsp; #{fid} &nbsp;|&nbsp; {row['solicitante']}
        &nbsp;|&nbsp; {row['area']} &nbsp;|&nbsp; {fmt_currency(row['total'])}
        &nbsp;|&nbsp; {PRIORIDAD_COLORS.get(row['prioridad'],'')} {row['prioridad']}
    </div>
</div>
""", unsafe_allow_html=True)

        st.code(ticket_texto, language=None)

        col_nota, col_btn = st.columns([4, 1])
        with col_nota:
            nueva_nota = st.text_input(
                "Nota de pedido N°",
                value="",
                placeholder="Ej: NP-2024-001, OC-456...",
                key=f"nota_input_{fid}",
                help="Números y/o caracteres identificatorios"
            )
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 Guardar", key=f"guardar_{fid}", type="primary"):
                if not nueva_nota.strip():
                    st.warning("Ingresá un número de nota antes de guardar.")
                else:
                    try:
                        with conn.session as session:
                            session.execute(
                                text("""UPDATE formularios 
                                        SET nota_de_pedido    = :nota,
                                            fecha_nota_pedido = :fecha
                                        WHERE id = :id"""),
                                {
                                    "nota":  nueva_nota.strip(),
                                    "fecha": datetime.now(timezone.utc),
                                    "id":    fid,
                                }
                            )
                            session.commit()
                        st.success(f"✅ Nota **{nueva_nota.strip()}** asignada al formulario #{fid}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
        st.divider()

# ══════════════════════════════════════════════════════════════════════════
# SECCIÓN 2 — LISTA CON NOTA ASIGNADA
# ══════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader(f"📋 Notas de pedido asignadas ({len(df_con_nota)})")

if df_con_nota.empty:
    st.info("Aún no hay notas de pedido asignadas.")
else:
    # ─── Tabla editable ────────────────────────────────────────────────────
    df_tabla = df_con_nota[[
        "id", "nota_de_pedido","fecha_nota_pedido", "solicitante", "area",
        "bien_servicio", "cantidad", "unidad_medida",
        "total", "tipo_gasto", "prioridad", "fecha_requerimiento",
        "fecha_aut2"
    ]].copy()

    df_tabla["total"]              = pd.to_numeric(df_tabla["total"], errors="coerce")
    df_tabla["fecha_requerimiento"] = pd.to_datetime(df_tabla["fecha_requerimiento"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("—")
    df_tabla["fecha_aut2"]         = pd.to_datetime(df_tabla["fecha_aut2"], utc=True).dt.tz_convert(ARG).dt.strftime("%d/%m/%Y %H:%M").fillna("—")
    df_tabla["fecha_nota_pedido"] = pd.to_datetime(df_tabla["fecha_nota_pedido"], utc=True).dt.tz_convert(ARG).dt.strftime("%d/%m/%Y %H:%M").fillna("—")

    df_tabla.columns = [
        "ID", "Nota de Pedido","Fecha Nota Pedido", "Solicitante", "Área",
        "Bien/Servicio", "Cantidad", "Unidad",
        "Total ($)", "Tipo Gasto", "Prioridad", "Fecha Requerida",
        "Fecha Aut.2"
    ]

    # Tabla editable solo en columna "Nota de Pedido"
    edited_df = st.data_editor(
        df_tabla,
        use_container_width=True,
        hide_index=True,
        disabled=[c for c in df_tabla.columns if c != "Nota de Pedido"],
        column_config={
            "ID":            st.column_config.NumberColumn(width="small"),
            "Nota de Pedido": st.column_config.TextColumn("Nota de Pedido", width="medium"),
            "Total ($)":     st.column_config.NumberColumn(format="$ %.2f"),
        },
        key="tabla_notas"
    )

    # Botón para guardar cambios de la tabla
    if st.button("💾 Guardar cambios de la tabla", type="primary"):
        cambios = 0
        try:
            with conn.session as session:
                for i, edit_row in edited_df.iterrows():
                    orig = df_tabla.loc[i, "Nota de Pedido"]
                    nuevo = str(edit_row["Nota de Pedido"]).strip()
                    if nuevo != orig:
                        session.execute(
                            text("UPDATE formularios SET nota_de_pedido = :nota WHERE id = :id"),
                            {"nota": nuevo, "id": int(edit_row["ID"])}
                        )
                        cambios += 1
                session.commit()
            if cambios > 0:
                st.success(f"✅ {cambios} registro(s) actualizados.")
                st.rerun()
            else:
                st.info("No se detectaron cambios.")
        except Exception as e:
            st.error(f"❌ Error al guardar: {e}")

    st.markdown(f"**💰 Total acumulado: {fmt_currency(pd.to_numeric(df_con_nota['total'], errors='coerce').sum())}**")

    # ─── Exportar a Excel ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ⬇️ Exportar")

    def generar_excel(dataframe):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            dataframe.to_excel(writer, index=False, sheet_name="Notas de Pedido")
            ws = writer.sheets["Notas de Pedido"]
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col) + 4
                ws.column_dimensions[col[0].column_letter].width = min(max_len, 40)
        return output.getvalue()

    excel_data = generar_excel(df_tabla)

    st.download_button(
        label="📥 Exportar a Excel (.xlsx)",
        data=excel_data,
        file_name="notas_de_pedido.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
