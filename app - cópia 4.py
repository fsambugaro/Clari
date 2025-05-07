import streamlit as st
import pandas as pd
import plotly.express as px
import os
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# 1) Configurações iniciais
st.set_page_config(page_title="Dashboard Pipeline LATAM", layout="wide")
# CSS para tema escuro geral e AgGrid
st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"], .block-container,
    [data-testid="stSidebar"], header, [data-testid="stToolbar"] {
        background-color: #111111 !important;
        color: #FFFFFF !important;
    }
    .stButton>button, .stSelectbox>div>div, .stMultiselect>div>div {
        background-color: #222222 !important;
        color: #FFFFFF !important;
    }
    /* AgGrid tema escuro com fundo preto e texto branco */
    .ag-theme-streamlit-dark .ag-root-wrapper,
    .ag-theme-streamlit-dark .ag-header,
    .ag-theme-streamlit-dark .ag-cell,
    .ag-theme-streamlit-dark .ag-header-cell {
        background-color: #000000 !important;
        color: #FFFFFF    !important;
    }
    .ag-theme-streamlit-dark .ag-header-cell {
        background-color: #111111 !important;
    }
    </style>
    """, unsafe_allow_html=True
)

# 2) Título
st.title("📊 Dashboard Pipeline LATAM")

# 3) Caminho dos CSVs
DIR = os.getcwd()

# 4) Lista de CSVs disponíveis
@st.cache_data
def list_csv_files():
    files = [f for f in os.listdir(DIR) if f.lower().endswith('.csv')]
    return sorted(files)

# 5) Carrega e sanitiza o CSV
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(os.path.join(DIR, file_path))
    df.columns = df.columns.str.strip()
    df['Opportunity'] = df.get('Opportunity', df.get('Opportunity ID', ''))
    df['Sales Team Member'] = df.get('Sales Team Member', df.get('Owner', '')).astype(str).str.strip()
    df['Stage'] = df['Stage'].astype(str).str.strip()
    df['Close Date'] = pd.to_datetime(df['Close Date'], errors='coerce')
    df['Total New ASV'] = (
        df['Total New ASV'].astype(str)
          .str.replace(r"[\$,]", '', regex=True)
          .astype(float)
    )
    return df

# 6) Sidebar: seleção de CSV
st.sidebar.header('📂 Selecione o CSV')
csv_files = list_csv_files()
selected_file = st.sidebar.selectbox('Arquivo:', [''] + csv_files)
if not selected_file:
    st.info('Selecione um CSV para continuar')
    st.stop()

df = load_data(selected_file)

# 7) Totais Pipeline e Won
total_pipeline = df[df['Stage'].isin([
    '03 - Opportunity Qualification',
    '05 - Solution Definition and Validation',
    '06 - Customer Commit'
])]['Total New ASV'].sum()
total_won = df[df['Stage'].isin(['07 - Execute to Close','Closed - Booked'])]['Total New ASV'].sum()
st.subheader(f"Total Pipeline: {total_pipeline:,.2f}   Total Won: {total_won:,.2f}")

# 8) Sidebar: filtros
st.sidebar.header('🔍 Filtros')
# Sales Team Member
members = ['Todos'] + sorted(df['Sales Team Member'].unique())
sel_member = st.sidebar.selectbox('Sales Team Member', members)
if sel_member != 'Todos':
    df = df[df['Sales Team Member'] == sel_member]
# Sales Stage
stages = sorted(df['Stage'].unique())
sel_stages = st.sidebar.multiselect('Sales Stage', stages, default=stages)
if sel_stages:
    df = df[df['Stage'].isin(sel_stages)]
# Forecast Indicator
if 'Forecast Indicator' in df.columns:
    opts = ['Todos'] + sorted(df['Forecast Indicator'].dropna().unique())
    sel_fc = st.sidebar.selectbox('Forecast Indicator', opts)
    if sel_fc != 'Todos':
        df = df[df['Forecast Indicator'] == sel_fc]
# Sub Territory
if 'Sub Territory' in df.columns:
    opts = ['Todos'] + sorted(df['Sub Territory'].dropna().unique())
    sel_stt = st.sidebar.selectbox('Sub Territory', opts)
    if sel_stt != 'Todos':
        df = df[df['Sub Territory'] == sel_stt]

# 9) Filtros adicionais
st.sidebar.header('🔧 Filtros adicionais')
exclude = [
    'Opportunity','Sales Team Member','Stage','Close Date','Total New ASV',
    'Forecast Indicator','Sub Territory','Record Owner','Account Name','Account Name.1',
    'Days Since Next Steps Modified','Next Steps','Renewal Bookings','Total DMe Est HASV',
    'Accept into Sales Pipeline','Forecast Notes','Rep Segment','Original Close Date',
    'Total Attrition','Sub Territory (Territory)','Accept into Sales Pipeline.1',
    'Total TSV','Close Reason Detail','Created Date','Forecast','ProbByClose',
    'Currency','Opportunity ID','Opportunity Currency','Clari Score'
]
for col in df.columns:
    if col not in exclude:
        vals = sorted(df[col].dropna().unique())
        sel = st.sidebar.multiselect(col, vals)
        if sel:
            df = df[df[col].isin(sel)]

# 10) Pipeline por Fase
st.header('🔍 Pipeline por Fase')
order = [
    '02 - Prospect','03 - Opportunity Qualification','05 - Solution Definition and Validation',
    '06 - Customer Commit','07 - Execute to Close','Closed - Booked'
]
phase = df[df['Stage'].isin(order)].groupby('Stage')['Total New ASV'].sum().reindex(order).reset_index()
fig_phase = px.bar(
    phase, x='Total New ASV', y='Stage', orientation='h', template='plotly_dark', text='Total New ASV',
    color='Stage', color_discrete_sequence=px.colors.qualitative.Vivid
)
fig_phase.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
st.plotly_chart(fig_phase, use_container_width=True)

# 11) Pipeline Semanal
st.header('📈 Pipeline Semanal')
df_week = df.dropna(subset=['Close Date']).copy()
df_week['Week'] = df_week['Close Date'].dt.to_period('W').dt.to_timestamp()
weekly = df_week.groupby('Week')['Total New ASV'].sum().reset_index()
fig_week = px.line(weekly, x='Week', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig_week.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig_week, use_container_width=True)

# 12) Pipeline Mensal
st.header('📆 Pipeline Mensal')
monthly = df_week.copy()
monthly['Month'] = monthly['Close Date'].dt.to_period('M').dt.to_timestamp()
monthly = monthly.groupby('Month')['Total New ASV'].sum().reset_index()
fig_month = px.line(monthly, x='Month', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig_month.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig_month, use_container_width=True)

# 13) Ranking de Vendedores
st.header('🏆 Ranking de Vendedores')
rk_df = df.groupby('Sales Team Member')['Total New ASV'].sum().reset_index()
rk_df = rk_df.sort_values('Total New ASV', ascending=False)
rk_df['Rank'] = range(1, len(rk_df) + 1)
rk_df['Total New ASV'] = rk_df['Total New ASV'].map('${:,.2f}'.format)
st.table(rk_df[['Rank','Sales Team Member','Total New ASV']])

# 14) Gráficos adicionais
extras = [
    ('Forecast Indicator','Pipeline por Forecast Indicator'),
    ('Licensing Program Type','Pipeline por Licensing Program Type'),
    ('Licensing Program','Pipeline por Licensing Program'),
    ('Major OLPG1','Pipeline por Major OLPG1')
]
for col, title in extras:
    if col in df.columns:
        st.header(f'📊 {title}')
        dcol = df.groupby(col)['Total New ASV'].sum().reset_index()
        fig = px.bar(dcol, x=col, y='Total New ASV', color=col,
            color_discrete_sequence=px.colors.qualitative.Vivid,
            template='plotly_dark', text='Total New ASV')
        fig.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
        st.plotly_chart(fig, use_container_width=True)

# 15) Dados Brutos e ficha detalhada
st.header('📋 Dados Brutos')
disp_df = df.copy()
disp_df['Total New ASV'] = disp_df['Total New ASV'].map('{:,.2f}'.format)
# Configura AgGrid com tema escuro, estilo personalizado e seleção única sem checkbox
builder = GridOptionsBuilder.from_dataframe(disp_df)
builder.configure_default_column(cellStyle={'color':'white','backgroundColor':'#000000'})
builder.configure_selection(selection_mode='single', use_checkbox=False)
grid_response = AgGrid(
    disp_df,
    gridOptions=builder.build(),
    theme='streamlit-dark',
    update_mode=GridUpdateMode.SELECTION_CHANGED
)
selected = grid_response['selected_rows']
if isinstance(selected, list) and len(selected) == 1:
    rec = selected[0]
    st.markdown(f"### 🗂 Detalhes: {rec.get('Opportunity','')}")
    for key, val in rec.items():
        st.markdown(f"- **{key}:** {val}")