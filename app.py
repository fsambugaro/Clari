# app.py

import streamlit as st
import pandas as pd
import plotly.express as px

# Configurações gerais
st.set_page_config(page_title="Dashboard Pipeline LATAM", layout="wide")
st.title("📊 Dashboard Pipeline LATAM")

@st.cache_data
def load_data_from_file(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    # Limpeza básica
    df.columns = df.columns.str.strip()
    df["Sales Team Member"] = df.get("Sales Team Member", df.get("Owner","")).astype(str).str.strip()
    df["Stage"] = df["Stage"].astype(str).str.strip()
    df["Close Date"] = pd.to_datetime(df["Close Date"], errors="coerce")
    df["Total New ASV"] = (
        df["Total New ASV"].astype(str)
           .str.replace(r"[\$,]","",regex=True)
           .astype(float)
    )
    return df

# 1) Upload do CSV
uploaded = st.file_uploader("Envie seu CSV de pipeline", type="csv")
if not uploaded:
    st.info("Por favor, faça o upload do seu arquivo CSV para prosseguir.")
    st.stop()

# 2) Carrega dados via uploader
df = load_data_from_file(uploaded)

# 3) Filtro inicial por Sales Team Member
members = ["Todos"] + sorted(df["Sales Team Member"].unique())
selected_member = st.selectbox("Filtrar por Sales Team Member:", members)
if selected_member != "Todos":
    df = df[df["Sales Team Member"] == selected_member]
    st.subheader(f"Filtrado por: {selected_member}")
else:
    st.subheader("Visão geral (todos os membros)")

# 4) Filtros adicionais
st.subheader("Filtros adicionais")
ignore = [
    "Sales Team Member","Stage","Close Date","Total New ASV",
    "Record Owner","Account Name 1","Currency","Opportunity ID",
    "Opportunity Currency","Clari Score"
]
filter_cols = [c for c in df.columns if c not in ignore]
cols_per_row = 3
for i in range(0, len(filter_cols), cols_per_row):
    cols = st.columns(cols_per_row)
    for j, col in enumerate(filter_cols[i:i+cols_per_row]):
        with cols[j]:
            opts = df[col].dropna().unique().tolist()
            sel = st.multiselect(col, opts, key=f"f_{col}")
            if sel:
                df = df[df[col].isin(sel)]

# 5) Ordem customizada de fases
ordered_stages = [
    "02 - Prospect","03 - Opportunity Qualification",
    "05 - Solution Definition and Validation","06 - Customer Commit",
    "07 - Execute to Close","Closed - Booked"
]

# 6) Gráficos e tabelas (igual à sua versão anterior)
# Pipeline por Fase
st.header("🔍 Pipeline por Fase")
stage_data = (
    df[df["Stage"].isin(ordered_stages)]
      .groupby("Stage", as_index=False)["Total New ASV"].sum()
)
stage_data["Stage"] = pd.Categorical(stage_data["Stage"], categories=ordered_stages, ordered=True)
fig1 = px.bar(stage_data, x="Total New ASV", y="Stage", orientation="h",
              color="Stage", template="plotly_dark", title="Pipeline por Fase")
st.plotly_chart(fig1, use_container_width=True)

# Pipeline Mensal
st.header("📈 Pipeline Mensal")
temp = df.dropna(subset=["Close Date"]).copy()
temp["Month"] = temp["Close Date"].dt.to_period("M").dt.to_timestamp()
monthly = temp.groupby("Month")["Total New ASV"].sum().reset_index()
fig2 = px.line(monthly, x="Month", y="Total New ASV", markers=True,
               template="plotly_dark", title="Pipeline ao Longo do Tempo")
st.plotly_chart(fig2, use_container_width=True)

# Ranking
st.header("🏆 Ranking de Membros da Equipe")
rank = df.groupby("Sales Team Member", as_index=False)["Total New ASV"].sum().sort_values("Total New ASV", ascending=False)
rank["Total New ASV"] = rank["Total New ASV"].map("${:,.2f}".format)
st.table(rank)

# Forecast Indicator
st.header("📊 Forecast Indicator")
if "Forecast Indicator" in df.columns:
    fc = df.groupby("Forecast Indicator", as_index=False)["Total New ASV"].sum()
    fig3 = px.bar(fc, x="Forecast Indicator", y="Total New ASV",
                  template="plotly_dark", title="Pipeline por Forecast Indicator")
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Coluna 'Forecast Indicator' ausente.")

# Licensing Program Type
st.header("📊 Licensing Program Type")
if "Licensing Program Type" in df.columns:
    lt = df.groupby("Licensing Program Type", as_index=False)["Total New ASV"].sum()
    fig4 = px.bar(lt, x="Licensing Program Type", y="Total New ASV",
                  template="plotly_dark", title="Pipeline por Licensing Program Type")
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("Coluna 'Licensing Program Type' ausente.")

# Licensing Program
st.header("📊 Licensing Program")
if "Licensing Program" in df.columns:
    lp = df.groupby("Licensing Program", as_index=False)["Total New ASV"].sum()
    fig5 = px.bar(lp, x="Licensing Program", y="Total New ASV",
                  template="plotly_dark", title="Pipeline por Licensing Program")
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("Coluna 'Licensing Program' ausente.")

# Major OLPG1
st.header("📊 Major OLPG1")
if "Major OLPG1" in df.columns:
    mo = df.groupby("Major OLPG1", as_index=False)["Total New ASV"].sum()
    fig6 = px.bar(mo, x="Major OLPG1", y="Total New ASV",
                  template="plotly_dark", title="Pipeline por Major OLPG1")
    st.plotly_chart(fig6, use_container_width=True)
else:
    st.info("Coluna 'Major OLPG1' ausente.")

# Dados brutos
st.header("📋 Dados Brutos")
st.dataframe(df)
