"""
02_dashboard.py — Dashboard con métricas, filtros y gráficos Plotly.
Acceso: Perfiles 1-4.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta , timezone
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import require_page_access, get_connection, fmt_currency
import json
from io import BytesIO

def expandir_items(df):
    rows = []
    for _, row in df.iterrows():
        items_val = row.get("items")
        tiene_items = (
            items_val is not None and
            not (isinstance(items_val, float) and pd.isna(items_val)) and
            str(items_val).strip() not in ("", "None", "nan")
        )
        if tiene_items:
            try:
                items = json.loads(items_val) if isinstance(items_val, str) else items_val
                if isinstance(items, list) and len(items) > 1:
                    for item in items:
                        r = row.copy()
                        r["bien_servicio"]   = item["bien_servicio"]
                        r["unidad_medida"]   = item["unidad_medida"]
                        r["precio_unitario"] = item["precio_unitario"]
                        r["cantidad"]        = item["cantidad"]
                        r["total"]           = item["subtotal"]
                        rows.append(r)
                    continue
            except:
                pass
        rows.append(row)
    return pd.DataFrame(rows) if rows else df.iloc[0:0]



require_page_access("dashboard")

st.title("📊 Dashboard — Sistema de Autorizaciones")
st.caption("Vista general de todas las solicitudes de gasto registradas.")

conn = get_connection()

# ─── Cargar datos ──────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_data():
    return conn.query("SELECT * FROM formularios ORDER BY created_at DESC", ttl=0)

try:
    df = load_data()
except Exception as e:
    st.error(f"❌ Error al conectar con la base de datos: {e}")
    st.info("Asegúrate de configurar `.streamlit/secrets.toml` con las credenciales PostgreSQL.")
    st.stop()

if df.empty:
    st.warning("📭 No hay formularios registrados aún. Ve a **Carga Formulario** para agregar.")
    st.stop()

# Convertir tipos
df["total"]      = pd.to_numeric(df["total"], errors="coerce").fillna(0)
df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
df["fecha_aut1"] = pd.to_datetime(df["fecha_aut1"], utc=True)
df["fecha_aut2"] = pd.to_datetime(df["fecha_aut2"], utc=True)

# ─── Filtros ───────────────────────────────────────────────────────────────
with st.expander("🔍 Filtros", expanded=False):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        areas = ["Todas"] + sorted(df["area"].dropna().unique().tolist())
        sel_area = st.multiselect("Área", options=df["area"].dropna().unique().tolist())
    with col2:
        sel_prioridad = st.multiselect(
            "Prioridad",
            options=["Alta", "Media", "Baja"],
        )
    with col3:
        sel_aut1 = st.selectbox("Autorizado 1", ["Todos", "Sí", "No"])
    with col4:
        sel_aut2 = st.selectbox("Autorizado 2", ["Todos", "Sí", "No"])

    date_range = st.date_input(
        "Rango de fechas",
        value=(df["created_at"].min().date(), df["created_at"].max().date())
        if not df["created_at"].isna().all() else (datetime.today().date(), datetime.today().date()),
    )

# Aplicar filtros
df_filtered = df.copy()
if sel_area:
    df_filtered = df_filtered[df_filtered["area"].isin(sel_area)]
if sel_prioridad:
    df_filtered = df_filtered[df_filtered["prioridad"].isin(sel_prioridad)]
if sel_aut1 == "Sí":
    df_filtered = df_filtered[df_filtered["autorizado1"] == True]
elif sel_aut1 == "No":
    df_filtered = df_filtered[df_filtered["autorizado1"] != True]
if sel_aut2 == "Sí":
    df_filtered = df_filtered[df_filtered["autorizado2"] == True]
elif sel_aut2 == "No":
    df_filtered = df_filtered[df_filtered["autorizado2"] != True]
if len(date_range) == 2 and not df_filtered["created_at"].isna().all():
    d_from = pd.Timestamp(date_range[0], tz="UTC")
    d_to   = pd.Timestamp(date_range[1], tz="UTC") + pd.Timedelta(days=1)
    df_filtered = df_filtered[
        (df_filtered["created_at"] >= d_from) & (df_filtered["created_at"] <= d_to)
    ]

st.divider()

# ─── KPIs ──────────────────────────────────────────────────────────────────
total_registros   = len(df_filtered)
total_monto       = df_filtered["total"].sum()
aut1_count        = df_filtered["autorizado1"].sum() if "autorizado1" in df_filtered else 0
aut2_count        = df_filtered["autorizado2"].sum() if "autorizado2" in df_filtered else 0
monto_aut1        = df_filtered.loc[df_filtered["autorizado1"] == True, "total"].sum()
pct_aprobado      = (aut2_count / total_registros * 100) if total_registros > 0 else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📋 Total Formularios",    f"{total_registros:,}")
k2.metric("💰 Monto Total",          fmt_currency(total_monto))
k3.metric("✅ Aprobados (Aut. 1)",   f"{int(aut1_count):,}")
k4.metric("🔐 Aprobados (Aut. 2)",   f"{int(aut2_count):,}")
k5.metric("📈 % Aprobación Final",   f"{pct_aprobado:.1f}%")

st.divider()

# ─── Gráficos ──────────────────────────────────────────────────────────────
row1_col1, row1_col2 = st.columns(2)

# Pie: tipo de gasto
with row1_col1:
    st.subheader("🥧 Por Tipo de Gasto")
    if not df_filtered.empty:
        pie_data = df_filtered.groupby("tipo_gasto")["total"].sum().reset_index()
        fig_pie = px.pie(
            pie_data,
            names="tipo_gasto",
            values="total",
            color_discrete_sequence=px.colors.qualitative.Set3,
            hole=0.35,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=320)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Sin datos para mostrar.")

# Bar: total por prioridad
with row1_col2:
    st.subheader("📊 Total $ por Prioridad")
    if not df_filtered.empty:
        bar_data = df_filtered.groupby("prioridad")["total"].sum().reindex(
            ["Alta", "Media", "Baja"], fill_value=0
        ).reset_index()
        bar_data.columns = ["Prioridad", "Total"]
        color_map = {"Alta": "#ef4444", "Media": "#f59e0b", "Baja": "#22c55e"}
        fig_bar = px.bar(
            bar_data,
            x="Prioridad",
            y="Total",
            color="Prioridad",
            color_discrete_map=color_map,
            text_auto=".2s",
        )
        fig_bar.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20), height=320)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Sin datos para mostrar.")

# Línea: evolución últimos 30 días
st.subheader("📈 Evolución de Montos — Últimos 30 días")
if not df_filtered.empty and not df_filtered["created_at"].isna().all():
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    df_line = df_filtered[df_filtered["created_at"] >= cutoff].copy()
    if not df_line.empty:
        df_line["fecha"] = df_line["created_at"].dt.date
        line_data = df_line.groupby("fecha")["total"].sum().reset_index()
        line_data.columns = ["Fecha", "Total"]
        fig_line = px.area(
            line_data,
            x="Fecha",
            y="Total",
            markers=True,
            color_discrete_sequence=["#3b82f6"],
        )
        fig_line.update_layout(margin=dict(t=10, b=20, l=20, r=20), height=280)
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No hay registros en los últimos 30 días.")
else:
    st.info("Sin datos de fechas disponibles.")

# Estado de autorizaciones (barras apiladas)
st.subheader("🔄 Estado de Autorizaciones por Área")
if not df_filtered.empty:
    status_df = df_filtered.copy()
    status_df["estado"] = status_df.apply(
        lambda r: "Aprobado Final" if r["autorizado2"] else
                  ("Aut. 1 OK" if r["autorizado1"] else "Pendiente"),
        axis=1
    )
    estado_area = status_df.groupby(["area", "estado"]).size().reset_index(name="count")
    fig_stack = px.bar(
        estado_area,
        x="area",
        y="count",
        color="estado",
        barmode="stack",
        color_discrete_map={
            "Pendiente":     "#e5e7eb",
            "Aut. 1 OK":     "#fbbf24",
            "Aprobado Final": "#22c55e",
        },
    )
    fig_stack.update_layout(
        xaxis_title="Área",
        yaxis_title="Cantidad",
        legend_title="Estado",
        height=300,
        margin=dict(t=10, b=20, l=20, r=20),
    )
    st.plotly_chart(fig_stack, use_container_width=True)

st.divider()

# ─── Tabla de datos ────────────────────────────────────────────────────────
st.subheader(f"📋 Listado de Formularios ({len(df_filtered)} registros)")


df_display_expandido = expandir_items(df_filtered)
# Formatear para mostrar
df_display = df_filtered[[
    "id", "solicitante", "area", "bien_servicio", "unidad_medida",
    "precio_unitario", "cantidad", "total", "tipo_gasto", "prioridad",
    "fecha_requerimiento",
    "gasto_escuelas", "autorizado1", "fecha_aut1", "autorizado2", "fecha_aut2", "created_at"
]].copy()

df_display["precio_unitario"] = df_display["precio_unitario"].apply(lambda x: f"$ {x:,.2f}")
df_display["total"]           = df_display["total"].apply(lambda x: f"$ {x:,.2f}")
df_display["gasto_escuelas"]  = df_display["gasto_escuelas"].apply(lambda x: "✅" if x else "❌")
df_display["autorizado1"]     = df_display["autorizado1"].apply(lambda x: "✅" if x else "⏳")
df_display["autorizado2"]     = df_display["autorizado2"].apply(lambda x: "✅" if x else "⏳")
ARG = "America/Argentina/Buenos_Aires"
df_display["fecha_requerimiento"] = pd.to_datetime(df_display["fecha_requerimiento"]).dt.strftime("%d/%m/%Y").fillna("—")
df_display["fecha_aut1"]  = pd.to_datetime(df_display["fecha_aut1"],  utc=True).dt.tz_convert(ARG).dt.strftime("%d/%m/%Y %H:%M").fillna("—")
df_display["fecha_aut2"]  = pd.to_datetime(df_display["fecha_aut2"],  utc=True).dt.tz_convert(ARG).dt.strftime("%d/%m/%Y %H:%M").fillna("—")
df_display["created_at"]  = pd.to_datetime(df_display["created_at"],  utc=True).dt.tz_convert(ARG).dt.strftime("%d/%m/%Y %H:%M").fillna("—")

df_display.columns = [
    "ID", "Solicitante", "Área", "Bien/Servicio", "Unidad",
    "P. Unitario", "Cantidad", "Total", "Tipo Gasto", "Prioridad",
    "Fecha Requerida",
    "Escuelas", "Aut. 1", "Fecha Aut.1", "Aut. 2", "Fecha Aut.2", "Creado"
]

st.dataframe(df_display, use_container_width=True, hide_index=True)

# Totales
total_sum = df_filtered["total"].sum()
st.markdown(f"**💰 Suma total de la selección: {fmt_currency(total_sum)}**")

# Descarga Excel
from io import BytesIO

def generar_excel(dataframe):
    df_excel = dataframe.copy()
    # Eliminar timezone de todas las columnas datetime
    for col in df_excel.columns:
        if pd.api.types.is_datetime64_any_dtype(df_excel[col]):
            df_excel[col] = df_excel[col].dt.tz_localize(None) \
                if df_excel[col].dt.tz is None \
                else df_excel[col].dt.tz_convert(None)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_excel.to_excel(writer, index=False, sheet_name="Formularios")
        ws = writer.sheets["Formularios"]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col) + 4
            ws.column_dimensions[col[0].column_letter].width = min(max_len, 45)
    return output.getvalue()

st.download_button(
    label="📥 Exportar a Excel (.xlsx)",
    data=generar_excel(df_filtered),
    file_name=f"formularios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
