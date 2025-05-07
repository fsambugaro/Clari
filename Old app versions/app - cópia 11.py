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
    html, body, [data-testid=\"stAppViewContainer\"], .block-container,
    [data-testid=\"stSidebar\"], header, [data-testid=\"stToolbar\"] {
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
        color: #FFFFFF !important;
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

# 4) Lista de CSVs
@st.cache_data
def list_csv_files():
    return sorted([f for f in os.listdir(DIR) if f.lower().endswith('.csv')])

# 5) Carrega e sanitiza dados
@st.cache_data
def load_data(path):
    df = pd.read_csv(os.path.join(DIR, path))
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

# 6) Seleção de CSV
st.sidebar.header('📂 Selecione o CSV')
file = st.sidebar.selectbox('Arquivo:', [''] + list_csv_files())
if not file:
    st.info('Selecione um CSV para continuar')
    st.stop()

df = load_data(file)

# 7) Totais
total_pipeline = df[df['Stage'].isin([
    '03 - Opportunity Qualification',
    '05 - Solution Definition and Validation',
    '06 - Customer Commit'
])]['Total New ASV'].sum()
total_won = df[df['Stage'].isin(['07 - Execute to Close','Closed - Booked'])]['Total New ASV'].sum()
st.subheader(f"Total Pipeline: {total_pipeline:,.2f}   Total Won: {total_won:,.2f}")

# 8) Filtros básicos
st.sidebar.header('🔍 Filtros')
members = ['Todos'] + sorted(df['Sales Team Member'].unique())
sel_member = st.sidebar.selectbox('Sales Team Member', members)
if sel_member != 'Todos': df = df[df['Sales Team Member']==sel_member]
stages = sorted(df['Stage'].unique())
sel_stages = st.sidebar.multiselect('Sales Stage', stages, default=stages)
if sel_stages: df = df[df['Stage'].isin(sel_stages)]
if 'Forecast Indicator' in df.columns:
    opts = ['Todos'] + sorted(df['Forecast Indicator'].dropna().unique())
    sel_fc = st.sidebar.selectbox('Forecast Indicator', opts)
    if sel_fc!='Todos': df = df[df['Forecast Indicator']==sel_fc]
if 'Sub Territory' in df.columns:
    opts = ['Todos'] + sorted(df['Sub Territory'].dropna().unique())
    sel_stt = st.sidebar.selectbox('Sub Territory', opts)
    if sel_stt!='Todos': df = df[df['Sub Territory']==sel_stt]

# 9) Filtros adicionais
st.sidebar.header('🔧 Filtros adicionais')
exclude = [
    'Opportunity','Sales Team Member','Stage','Close Date','Total New ASV',
    'Forecast Indicator','Sub Territory','Record Owner','Account Name','Account Name.1',
    'Days Since Next Steps Modified','Next Steps','Renewal Bookings','Total DMe Est HASV',
    'Accept into Sales Pipeline','Rep Segment','Forecast','ProbByClose','Forecast Notes',
    'Total TSV','Original Close Date','Deal Registration ID','Owner'
]
for col in df.columns:
    if col not in exclude:
        vals = sorted(df[col].dropna().unique())
        sel = st.sidebar.multiselect(col, vals)
        if sel: df = df[df[col].isin(sel)]

# 10) Pipeline por Fase
st.header('🔍 Pipeline por Fase')
order = ['02 - Prospect','03 - Opportunity Qualification','05 - Solution Definition and Validation',
         '06 - Customer Commit','07 - Execute to Close','Closed - Booked']
phase = df[df['Stage'].isin(order)].groupby('Stage')['Total New ASV'].sum().reindex(order).reset_index()
fig = px.bar(phase, x='Total New ASV', y='Stage', orientation='h', template='plotly_dark', text='Total New ASV', color='Stage', color_discrete_sequence=px.colors.qualitative.Vivid)
fig.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
st.plotly_chart(fig, use_container_width=True)

# 11) Pipeline Semanal
st.header('📈 Pipeline Semanal')
df_week = df.dropna(subset=['Close Date']).copy()
df_week['Week'] = df_week['Close Date'].dt.to_period('W').dt.to_timestamp()
weekly = df_week.groupby('Week')['Total New ASV'].sum().reset_index()
fig = px.line(weekly, x='Week', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig, use_container_width=True)

# 12) Pipeline Mensal
st.header('📆 Pipeline Mensal')
monthly = df_week.copy()
monthly['Month'] = monthly['Close Date'].dt.to_period('M').dt.to_timestamp()
monthly = monthly.groupby('Month')['Total New ASV'].sum().reset_index()
fig = px.line(monthly, x='Month', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig, use_container_width=True)

# 13) Ranking de Vendedores
st.header('🏆 Ranking de Vendedores')
rk = df.groupby('Sales Team Member')['Total New ASV'].sum().reset_index()
rk = rk.sort_values('Total New ASV', ascending=False)
rk['Rank'] = range(1, len(rk)+1)
rk['Total New ASV'] = rk['Total New ASV'].map('${:,.2f}'.format)
st.table(rk[['Rank','Sales Team Member','Total New ASV']])

# 14) Gráficos adicionais
extras = [('Forecast Indicator','Pipeline por Forecast Indicator'),('Licensing Program Type','Pipeline por Licensing Program Type'),('Licensing Program','Pipeline por Licensing Program'),('Major OLPG1','Pipeline por Major OLPG1')]
for col,title in extras:
    if col in df.columns:
        st.header(f'📊 {title}')
        dcol = df.groupby(col)['Total New ASV'].sum().reset_index()
        fig = px.bar(dcol, x=col, y='Total New ASV', color=col, color_discrete_sequence=px.colors.qualitative.Vivid, template='plotly_dark', text='Total New ASV')
        fig.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
        st.plotly_chart(fig, use_container_width=True)

# 15) Dados Brutos e ficha detalhada
st.header('📋 Dados Brutos')
disp = df.copy()
disp['Total New ASV'] = disp['Total New ASV'].map('{:,.2f}'.format)
builder = GridOptionsBuilder.from_dataframe(disp)
builder.configure_default_column(cellStyle={'color':'white','backgroundColor':'#000000'})
builder.configure_selection(selection_mode='single', use_checkbox=True)
grid_resp = AgGrid(disp, gridOptions=builder.build(), theme='streamlit-dark', update_mode=GridUpdateMode.SELECTION_CHANGED, height=500)
sel = grid_resp['selected_rows']
if isinstance(sel, pd.DataFrame): sel_list = sel.to_dict('records')
else: sel_list = sel or []
if sel_list:
    rec = sel_list[0]
    st.markdown("---")
    with st.expander(f"🗂 Ficha: {rec.get('Opportunity','')}", expanded=True):
        # 1) Exibir campos destacados em primeiro
        highlights = ['Stage','Total New ASV','Close Date','Total TSV','Original Close Date','Deal Registration ID','Owner']
        hl_cols = st.columns(3)
        for idx, key in enumerate(highlights):
            val = rec.get(key, '')
            with hl_cols[idx % 3]:
                st.markdown(f"<span style='color:#FFD700'><strong>{key}:</strong> {val}</span>", unsafe_allow_html=True)
        st.markdown("<hr/>", unsafe_allow_html=True)
        # 2) Exibir demais campos comuns em 3 colunas
        items = [(k,v) for k,v in rec.items() if k not in highlights + ['Forecast Notes','Next Steps']]
        cols = st.columns(3)
        for idx,(key,val) in enumerate(items):
            with cols[idx % 3]:
                st.markdown(f"**{key}:** {val}")
        # 3) Next Steps full width
        steps = rec.get('Next Steps', '')
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown("<span style='color:#FFD700'><strong>Next Steps:</strong></span>", unsafe_allow_html=True)
        st.write(steps)
        # 4) Forecast Notes full width
        notes = rec.get('Forecast Notes', '')
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown("<span style='color:#FFD700'><strong>Forecast Notes:</strong></span>", unsafe_allow_html=True)
        st.write(notes)