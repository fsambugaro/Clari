import streamlit as st
import pandas as pd
import plotly.express as px
import subprocess
import os

# Configuração da página
st.set_page_config(page_title="Dashboard Pipeline LATAM", layout="wide")
st.title("📊 Dashboard Pipeline LATAM")

# Constantes do GitHub
github_api = "https://api.github.com"
repo_owner = "fsambugaro"
repo_name = "Clari"
csv_dir = ""  # ajustar se os CSVs estiverem em subpasta

# Sincroniza repositório local com GitHub remoto
try:
    subprocess.run([
        "git", "-C", os.path.expanduser("~/Documents/Clari"),
        "pull", "origin", "main"
    ], check=True)
    st.write("✅ Repositório sincronizado com o GitHub.")
except Exception as e:
    st.error(f"Erro ao sincronizar repo: {e}")

# Lista de CSVs após pull
def list_csv_files():
    folder = os.path.expanduser("~/Documents/Clari")
    return sorted([f for f in os.listdir(folder) if f.lower().endswith('.csv')])

# Seleção de CSV
csv_files = list_csv_files()
st.sidebar.header('📂 Selecione o arquivo CSV')
selected_file = st.sidebar.selectbox('Arquivos disponíveis:', [''] + csv_files)
if not selected_file:
    st.info('Selecione um arquivo CSV para continuar.')
    st.stop()

# Carrega e sanitiza dados a partir de arquivo local
@st.cache_data
def load_and_sanitize(filename: str) -> pd.DataFrame:
    path = os.path.expanduser(f"~/Documents/Clari/{filename}")
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df['Sales Team Member'] = df.get('Sales Team Member', df.get('Owner','')).astype(str).str.strip()
    df['Stage'] = df['Stage'].astype(str).str.strip()
    df['Close Date'] = pd.to_datetime(df['Close Date'], errors='coerce')
    df['Total New ASV'] = (
        df['Total New ASV'].astype(str)
          .str.replace(r"[\$,]", '', regex=True)
          .astype(float)
    )
    return df

# Carrega dados
_df = load_and_sanitize(selected_file)
df = _df.copy()

# Filtros na sidebar
st.sidebar.header('🔍 Filtros')
members = ['Todos'] + sorted(df['Sales Team Member'].unique())
sel_member = st.sidebar.selectbox('Sales Team Member:', members)
if sel_member != 'Todos':
    df = df[df['Sales Team Member'] == sel_member]
stages = sorted(df['Stage'].unique())
sel_stages = st.sidebar.multiselect('Sales Stage:', stages, default=stages)
if sel_stages:
    df = df[df['Stage'].isin(sel_stages)]
ignore = ['Sales Team Member','Stage','Close Date','Total New ASV',
          'Record Owner','Account Name 1','Currency','Opportunity ID',
          'Opportunity Currency','Clari Score']
for col in [c for c in df.columns if c not in ignore]:
    opts = df[col].dropna().unique().tolist()
    sel = st.sidebar.multiselect(col, opts)
    if sel:
        df = df[df[col].isin(sel)]

# Formatação
def fmt(x): return f"{x:,.2f}"

# Pipeline por Fase
st.header('🔍 Pipeline por Fase')
st.write(f"Arquivo: **{selected_file}** | Membro: **{sel_member}** | Stages: **{', '.join(sel_stages)}**")
order = [
    '02 - Prospect','03 - Opportunity Qualification',
    '05 - Solution Definition and Validation','06 - Customer Commit',
    '07 - Execute to Close','Closed - Booked'
]
data1 = df[df['Stage'].isin(order)].groupby('Stage', as_index=False)['Total New ASV'].sum()
data1['Stage'] = pd.Categorical(data1['Stage'], categories=order, ordered=True)
fig1 = px.bar(
    data1, x='Total New ASV', y='Stage', orientation='h',
    color='Stage', color_discrete_sequence=px.colors.qualitative.Vivid,
    template='plotly_dark', text='Total New ASV'
)
fig1.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
st.plotly_chart(fig1, use_container_width=True)

# Pipeline Mensal
st.header('📈 Pipeline Mensal')
tmp = df.dropna(subset=['Close Date']).copy()
tmp['Month'] = tmp['Close Date'].dt.to_period('M').dt.to_timestamp()
mon = tmp.groupby('Month')['Total New ASV'].sum().reset_index()
fig2 = px.line(mon, x='Month', y='Total New ASV', markers=True,
               template='plotly_dark', text='Total New ASV')
fig2.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig2, use_container_width=True)

# Ranking de Membros
st.header('🏆 Ranking de Membros da Equipe')
rk = df.groupby('Sales Team Member', as_index=False)['Total New ASV'].sum().sort_values('Total New ASV', ascending=False)
rk['Total New ASV'] = rk['Total New ASV'].map(lambda x: f"${x:,.2f}")
st.table(rk)

# Forecast Indicator
st.header('📊 Forecast Indicator')
if 'Forecast Indicator' in df.columns:
    fc = df.groupby('Forecast Indicator', as_index=False)['Total New ASV'].sum()
    fig3 = px.bar(
        fc, x='Forecast Indicator', y='Total New ASV',
        color='Forecast Indicator', color_discrete_sequence=px.colors.qualitative.Vivid,
        template='plotly_dark', text='Total New ASV'
    )
    fig3.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Coluna 'Forecast Indicator' ausente.")

# Licensing Program Type
st.header('📊 Licensing Program Type')
if 'Licensing Program Type' in df.columns:
    lt = df.groupby('Licensing Program Type', as_index=False)['Total New ASV'].sum()
    fig4 = px.bar(
        lt, x='Licensing Program Type', y='Total New ASV',
        color='Licensing Program Type', color_discrete_sequence=px.colors.qualitative.Vivid,
        template='plotly_dark', text='Total New ASV'
    )
    fig4.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("Coluna 'Licensing Program Type' ausente.")

# Licensing Program
st.header('📊 Licensing Program')
if 'Licensing Program' in df.columns:
    lp = df.groupby('Licensing Program', as_index=False)['Total New ASV'].sum()
    fig5 = px.bar(
        lp, x='Licensing Program', y='Total New ASV',
        color='Licensing Program', color_discrete_sequence=px.colors.qualitative.Vivid,
        template='plotly_dark', text='Total New ASV'
    )
    fig5.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("Coluna 'Licensing Program' ausente.")

# Major OLPG1
st.header('📊 Major OLPG1')
if 'Major OLPG1' in df.columns:
    mo = df.groupby('Major OLPG1', as_index=False)['Total New ASV'].sum()
    fig6 = px.bar(
        mo, x='Major OLPG1', y='Total New ASV',
        color='Major OLPG1', color_discrete_sequence=px.colors.qualitative.Vivid,
        template='plotly_dark', text='Total New ASV'
    )
    fig6.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
    st.plotly_chart(fig6, use_container_width=True)
else:
    st.info("Coluna 'Major OLPG1' ausente.")

# Dados Brutos
st.header('📋 Dados Brutos')
if 'Total New ASV' in df.columns:
    df_disp = df.copy()
    df_disp['Total New ASV'] = df_disp['Total New ASV'].map(lambda x: fmt(x))
    st.dataframe(df_disp)
else:
    st.dataframe(df)
