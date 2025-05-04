import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# Configuração da página
st.set_page_config(page_title="Dashboard Pipeline LATAM", layout="wide")
st.title("📊 Dashboard Pipeline LATAM")

# Constantes do GitHub
GITHUB_API = "https://api.github.com"
REPO_OWNER = "fsambugaro"
REPO_NAME = "Clari"
CSV_DIR = ""  # use subpasta se necessário

@st.cache_data
def list_csv_files():
    """Lista arquivos CSV do repositório via API."""
    url = f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{CSV_DIR}"
    resp = requests.get(url)
    resp.raise_for_status()
    items = resp.json()
    return [item['name'] for item in items if item['type']=='file' and item['name'].lower().endswith('.csv')]

@st.cache_data
def load_and_sanitize(filename: str) -> pd.DataFrame:
    """Carrega CSV do raw GitHub e sanitiza as colunas."""
    raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{CSV_DIR}{filename}"
    df = pd.read_csv(raw_url)
    df.columns = df.columns.str.strip()
    df['Sales Team Member'] = df.get('Sales Team Member', df.get('Owner','')).astype(str).str.strip()
    df['Stage'] = df['Stage'].astype(str).str.strip()
    df['Close Date'] = pd.to_datetime(df['Close Date'], errors='coerce')
    # Sanitiza valor
    df['Total New ASV'] = (
        df['Total New ASV'].astype(str)
          .str.replace(r"[\$,]", '', regex=True)
          .astype(float)
    )
    return df

# 1) Seleção de arquivo CSV
st.sidebar.header('📂 Selecione o arquivo CSV')
csv_files = list_csv_files()
selected_file = st.sidebar.selectbox('Arquivos disponíveis:', [''] + csv_files)
if not selected_file:
    st.info('Por favor, selecione um arquivo CSV para carregar.')
    st.stop()

# 2) Carrega dados
df = load_and_sanitize(selected_file)

# 3) Filtros na sidebar
st.sidebar.header('🔍 Filtros')
# Filtro por Sales Team Member
members = ['Todos'] + sorted(df['Sales Team Member'].unique())
selected_member = st.sidebar.selectbox('Sales Team Member', members)
if selected_member != 'Todos':
    df = df[df['Sales Team Member'] == selected_member]

# Filtros adicionais
global_ignore = ['Sales Team Member','Stage','Close Date','Total New ASV',
                 'Record Owner','Account Name 1','Currency','Opportunity ID',
                 'Opportunity Currency','Clari Score']
for col in [c for c in df.columns if c not in global_ignore]:
    opts = df[col].dropna().unique().tolist()
    sel = st.sidebar.multiselect(col, opts)
    if sel:
        df = df[df[col].isin(sel)]

# 4) Pipeline por Fase
st.header('🔍 Pipeline por Fase')
st.write(f'Arquivo: **{selected_file}** | Filtrado por: **{selected_member}**')
stages_order = [
    '02 - Prospect','03 - Opportunity Qualification',
    '05 - Solution Definition and Validation','06 - Customer Commit',
    '07 - Execute to Close','Closed - Booked'
]
stage_data = (
    df[df['Stage'].isin(stages_order)]
      .groupby('Stage', as_index=False)['Total New ASV'].sum()
)
stage_data['Stage'] = pd.Categorical(stage_data['Stage'], categories=stages_order, ordered=True)
fig1 = px.bar(
    stage_data, x='Total New ASV', y='Stage', orientation='h',
    color='Stage', color_discrete_sequence=px.colors.qualitative.Vivid,
    template='plotly_dark', title='Pipeline por Fase', text='Total New ASV'
)
fig1.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
st.plotly_chart(fig1, use_container_width=True)

# 5) Pipeline Mensal
st.header('📈 Pipeline Mensal')
tmp = df.dropna(subset=['Close Date']).copy()
tmp['Month'] = tmp['Close Date'].dt.to_period('M').dt.to_timestamp()
monthly = tmp.groupby('Month')['Total New ASV'].sum().reset_index()
fig2 = px.line(
    monthly, x='Month', y='Total New ASV', markers=True,
    template='plotly_dark', title='Pipeline ao Longo do Tempo', text='Total New ASV'
)
fig2.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig2, use_container_width=True)

# 6) Ranking de Membros da Equipe
st.header('🏆 Ranking de Membros da Equipe')
rk = (
    df.groupby('Sales Team Member', as_index=False)['Total New ASV']
      .sum().sort_values('Total New ASV', ascending=False)
)
rk['Total New ASV'] = rk['Total New ASV'].map('${:,.2f}'.format)
st.table(rk)

# 7) Forecast Indicator
st.header('📊 Forecast Indicator')
if 'Forecast Indicator' in df.columns:
    fc = df.groupby('Forecast Indicator', as_index=False)['Total New ASV'].sum()
    fig3 = px.bar(
        fc, x='Forecast Indicator', y='Total New ASV',
        template='plotly_dark', text='Total New ASV'
    )
    fig3.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Coluna 'Forecast Indicator' ausente.")

# 8) Licensing Program Type
st.header('📊 Licensing Program Type')
if 'Licensing Program Type' in df.columns:
    lt = df.groupby('Licensing Program Type', as_index=False)['Total New ASV'].sum()
    fig4 = px.bar(
        lt, x='Licensing Program Type', y='Total New ASV',
        template='plotly_dark', text='Total New ASV'
    )
    fig4.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("Coluna 'Licensing Program Type' ausente.")

# 9) Licensing Program
st.header('📊 Licensing Program')
if 'Licensing Program' in df.columns:
    lp = df.groupby('Licensing Program', as_index=False)['Total New ASV'].sum()
    fig5 = px.bar(
        lp, x='Licensing Program', y='Total New ASV',
        template='plotly_dark', text='Total New ASV'
    )
    fig5.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("Coluna 'Licensing Program' ausente.")

# 10) Major OLPG1
st.header('📊 Major OLPG1')
if 'Major OLPG1' in df.columns:
    mo = df.groupby('Major OLPG1', as_index=False)['Total New ASV'].sum()
    fig6 = px.bar(
        mo, x='Major OLPG1', y='Total New ASV',
        template='plotly_dark', text='Total New ASV'
    )
    fig6.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
    st.plotly_chart(fig6, use_container_width=True)
else:
    st.info("Coluna 'Major OLPG1' ausente.")

# 11) Dados Brutos
st.header('📋 Dados Brutos')
if 'Total New ASV' in df.columns:
    df_disp = df.copy()
    df_disp['Total New ASV'] = df_disp['Total New ASV'].map(lambda x: f"{x:,.2f}")
    st.dataframe(df_disp)
else:
    st.dataframe(df)
