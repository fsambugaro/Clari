import streamlit as st
import pandas as pd
import plotly.express as px
import os
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

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

# 4) Lista de CSVs disponíveis
@st.cache_data
def list_csv_files():
    return sorted([f for f in os.listdir(DIR) if f.lower().endswith('.csv')])

# 5) Carrega e sanitiza dados
def load_data(path):
    df = pd.read_csv(os.path.join(DIR, path))
    df.columns = df.columns.str.strip()
    df['Opportunity'] = df.get('Opportunity', df.get('Opportunity ID', ''))
    df['Sales Team Member'] = df.get('Sales Team Member', df.get('Owner', '')).astype(str).str.strip()
    df['Stage'] = df['Stage'].astype(str).str.strip()
    df['Close Date'] = pd.to_datetime(df['Close Date'], errors='coerce')
    # mantém como float para ordenação
    df['Total New ASV'] = (
        df['Total New ASV'].astype(str)
          .str.replace(r"[\$,]", '', regex=True)
          .astype(float)
    )
    # Extrai Region de Sub Territory
    if 'Sub Territory' in df.columns:
        df['Region'] = df['Sub Territory'].astype(str).apply(
            lambda x: 'Hispanic' if 'Hispanic' in x else ('Brazil' if 'Brazil' in x else 'Other')
        )
    else:
        df['Region'] = 'Other'
    return df

# 6) Seleção de CSV
st.sidebar.header('📂 Selecione o CSV')
file = st.sidebar.selectbox('Arquivo:', [''] + list_csv_files())
if not file:
    st.info('Selecione um CSV para continuar')
    st.stop()

df = load_data(file)

# 7) Filtros básicos
st.sidebar.header('🔍 Filtros')
# Sales Team Member
tmembers = ['Todos'] + sorted(df['Sales Team Member'].unique())
sel_member = st.sidebar.selectbox('Sales Team Member', tmembers)
if sel_member != 'Todos':
    df = df[df['Sales Team Member'] == sel_member]
# Sales Stage (fechadas desmarcadas por padrão)
stages = sorted(df['Stage'].unique())
closed = ['Closed - Booked', 'Closed - Clean Up', 'Closed - Lost']
default_stages = [s for s in stages if s not in closed]
sel_stages = st.sidebar.multiselect('Sales Stage', stages, default=default_stages)
if sel_stages:
    df = df[df['Stage'].isin(sel_stages)]
# Region: Brazil / Hispanic
regions = ['Todos', 'Brazil', 'Hispanic']
sel_region = st.sidebar.selectbox('Region', regions)
if sel_region != 'Todos':
    df = df[df['Sub Territory'].astype(str).str.contains(sel_region, case=False, na=False)]

# 8) Totais após filtros iniciais
total_pipeline = df[df['Stage'].isin([
    '03 - Opportunity Qualification','05 - Solution Definition and Validation','06 - Customer Commit'
])]['Total New ASV'].sum()
total_won = df[df['Stage'].isin(['07 - Execute to Close','Closed - Booked'])]['Total New ASV'].sum()
st.subheader(f"Total Pipeline: {total_pipeline:,.2f}   Total Won: {total_won:,.2f}")

# 9) Filtros adicionais personalizados
st.sidebar.header('🔧 Filtros adicionais')
if 'Fiscal Quarter' in df.columns:
    sel_fq = st.sidebar.selectbox('Fiscal Quarter', ['Todos'] + sorted(df['Fiscal Quarter'].dropna().unique()))
    if sel_fq != 'Todos': df = df[df['Fiscal Quarter'] == sel_fq]
if 'Forecast Indicator' in df.columns:
    sel_fc = st.sidebar.selectbox('Forecast Indicator', ['Todos'] + sorted(df['Forecast Indicator'].dropna().unique()))
    if sel_fc != 'Todos': df = df[df['Forecast Indicator'] == sel_fc]
if 'Deal Registration ID' in df.columns:
    sel_drid = st.sidebar.selectbox('Deal Registration ID', ['Todos'] + sorted(df['Deal Registration ID'].dropna().unique()))
    if sel_drid != 'Todos': df = df[df['Deal Registration ID'] == sel_drid]
if 'Days Since Next Steps Modified' in df.columns:
    labels = ['<=7 dias','8-14 dias','15-30 dias','>30 dias']
    df['DaysGroup'] = pd.cut(df['Days Since Next Steps Modified'], bins=[0,7,14,30,float('inf')], labels=labels)
    sel_dg = st.sidebar.selectbox('Dias desde Next Steps', ['Todos'] + labels)
    if sel_dg != 'Todos': df = df[df['DaysGroup'] == sel_dg]
if 'Licensing Program Type' in df.columns:
    sel_lpt = st.sidebar.selectbox('Licensing Program Type', ['Todos'] + sorted(df['Licensing Program Type'].dropna().unique()))
    if sel_lpt != 'Todos': df = df[df['Licensing Program Type'] == sel_lpt]
if 'Opportunity' in df.columns:
    sel_op = st.sidebar.selectbox('Opportunity', ['Todos'] + sorted(df['Opportunity'].dropna().unique()))
    if sel_op != 'Todos': df = df[df['Opportunity'] == sel_op]
if 'Account Name' in df.columns:
    sel_an = st.sidebar.selectbox('Account Name', ['Todos'] + sorted(df['Account Name'].dropna().unique()))
    if sel_an != 'Todos': df = df[df['Account Name'] == sel_an]
if 'Account Address: State/Province' in df.columns:
    sel_state = st.sidebar.selectbox('Account Address: State/Province', ['Todos'] + sorted(df['Account Address: State/Province'].dropna().unique()))
    if sel_state != 'Todos': df = df[df['Account Address: State/Province'] == sel_state]

enum_df = df.copy()
edu_choice = st.sidebar.radio('Filtro EDU', ['All','EDU','Others'], index=0)
if edu_choice == 'EDU':
    df = enum_df[enum_df['Sub Territory'].str.contains('EDU', case=False, na=False)]
elif edu_choice == 'Others':
    df = enum_df[~enum_df['Sub Territory'].str.contains('EDU', case=False, na=False)]
else:
    df = enum_df

# 10) Pipeline por Fase
st.header('🔍 Pipeline por Fase')
order = ['02 - Prospect','03 - Opportunity Qualification','05 - Solution Definition and Validation',
         '06 - Customer Commit','07 - Execute to Close','Closed - Booked']
phase = df[df['Stage'].isin(order)].groupby('Stage')['Total New ASV'].sum().reindex(order).reset_index()
fig = px.bar(
    phase, x='Total New ASV', y='Stage', orientation='h', template='plotly_dark', text='Total New ASV',
    color='Stage', color_discrete_sequence=px.colors.qualitative.Vivid
)
fig.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
st.plotly_chart(fig, use_container_width=True)

# 11) Pipeline Semanal
st.header('📈 Pipeline Semanal')
df_week = df.dropna(subset=['Close Date']).copy()
df_week['Week'] = df_week['Close Date'].dt.to_period('W').dt.to_timestamp()
weekly = df_week.groupby('Week')['Total New ASV'].sum().reset_index()
fig = px.line(
    weekly, x='Week', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV'
)
fig.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig, use_container_width=True)

# 12) Pipeline Mensal
st.header('📆 Pipeline Mensal')
mon = df_week.copy()
mon['Month'] = mon['Close Date'].dt.to_period('M').dt.to_timestamp()
monthly = mon.groupby('Month')['Total New ASV'].sum().reset_index()
fig = px.line(
    monthly, x='Month', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV'
)
fig.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig, use_container_width=True)

# 13) Ranking de Vendedores
st.header('🏆 Ranking de Vendedores')
rk = df.groupby('Sales Team Member')['Total New ASV'].sum().reset_index().sort_values('Total New ASV', ascending=False)
rk['Rank'] = range(1, len(rk)+1)
rk['Total New ASV'] = rk['Total New ASV'].map('${:,.2f}'.format)
st.table(rk[['Rank','Sales Team Member','Total New ASV']])

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
        fig = px.bar(
            dcol, x=col, y='Total New ASV', color=col,
            color_discrete_sequence=px.colors.qualitative.Vivid,
            template='plotly_dark', text='Total New ASV'
        )
        fig.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
        st.plotly_chart(fig, use_container_width=True)

# 15) Dados Brutos e ficha detalhada
st.header('📋 Dados Brutos')
# Mantém Total New ASV como float para ordenação e formatação pt-BR via cellRenderer

# Prepara DataFrame para grid
disp = df.copy()
# Configura AgGrid
gb = GridOptionsBuilder.from_dataframe(disp)
# Tema escuro padrão
gb.configure_default_column(cellStyle={'color':'white','backgroundColor':'#000000'})
# Configura Total New ASV: tipo numérico, alinhamento à direita e formatação pt-BR
cell_renderer = JsCode(
    "function(params) { return params.value!=null ? params.value.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}) : ''; }"
)
gb.configure_column(
    'Total New ASV',
    type=['numericColumn','numberColumnFilter'],
    cellStyle={'textAlign':'right'},
    cellRenderer=cell_renderer
)
# Seleção única
gb.configure_selection(selection_mode='single', use_checkbox=True)

# Renderiza AgGrid com JsCode permitido
grid_resp = AgGrid(
    disp,
    gridOptions=gb.build(),
    theme='streamlit-dark',
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    allow_unsafe_jscode=True,
    height=500
)
# Captura seleção e exibe ficha detalhada
sel = grid_resp['selected_rows']
# Normaliza seleção para lista de registros
if isinstance(sel, pd.DataFrame):
    sel_list = sel.to_dict('records')
else:
    sel_list = sel or []
if sel_list:
    rec = sel_list[0]
    st.markdown('---')
    with st.expander(f"🗂 Ficha: {rec.get('Opportunity','')}", expanded=True):
        # Campos destacados
        highlights = [
            'Stage','Total New ASV','Close Date','Total TSV','Original Close Date',
            'Deal Registration ID','Owner','Total DMe Est HASV','Sales Team Member'
        ]
        cols = st.columns(3)
        for idx, key in enumerate(highlights):
            with cols[idx % 3]:
                st.markdown(
                    f"<span style='color:#FFD700'><strong>{key}:</strong> {rec.get(key,'')}"          
                    f"</span>",
                    unsafe_allow_html=True
                )
        st.markdown('<hr/>', unsafe_allow_html=True)
        # Demais campos
        items = [(k,v) for k,v in rec.items() if k not in highlights + ['Next Steps','Forecast Notes']]
        cols2 = st.columns(3)
        for idx,(k,v) in enumerate(items):
            with cols2[idx % 3]:
                st.markdown(f"**{k}:** {v}")
        # Next Steps e Forecast Notes
        st.markdown('<hr/>', unsafe_allow_html=True)
        st.markdown("<span style='color:#FFD700'><strong>Next Steps:</strong></span>", unsafe_allow_html=True)
        st.write(rec.get('Next Steps',''))
        st.markdown('<hr/>', unsafe_allow_html=True)
        st.markdown("<span style='color:#FFD700'><strong>Forecast Notes:</strong></span>", unsafe_allow_html=True)
        st.write(rec.get('Forecast Notes',''))
