import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import io
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
st.title("📊 LATAM Pipeline Dashboard")

import os
import streamlit as st  # já deve estar importado

# 3) Caminho dos CSVs — busca na subpasta "Data" ao lado do app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(BASE_DIR, "Data")

# Se a pasta não existir, interrompe com mensagem amigável
if not os.path.isdir(DIR):
    st.error(f"🚨 Pasta de dados não encontrada: {DIR}")
    st.stop()



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
    df['Total New ASV'] = (
        df['Total New ASV'].astype(str)
          .str.replace(r"[\$,]", '', regex=True)
          .astype(float)
    )
    # Converte campos numéricos adicionais para float, para alinhamento correto
    for col in ['Renewal Bookings','Total DMe Est HASV','Total Attrition','Total TSV','Total Renewal ASV']:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                     .str.replace(r"[\$,]", '', regex=True)
                     .astype(float)
            )
    if 'Sub Territory' in df.columns:
        df['Region'] = df['Sub Territory'].astype(str).apply(
            lambda x: 'Hispanic' if 'Hispanic' in x else ('Brazil' if 'Brazil' in x else 'Other')
        )
    else:
        df['Region'] = 'Other'
    return df

# 6) Seleção de CSV
st.sidebar.header('📂 Select CSV file')
file = st.sidebar.selectbox('File:', [''] + list_csv_files())
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
# Sales Stage (fechadas Clean Up e Lost desmarcadas por padrão, Closed - Booked marcado)
stages = sorted(df['Stage'].unique())
closed = ['Closed - Clean Up', 'Closed - Lost']  # Clean Up e Lost desmarcadas
# Closed - Booked estará marcado por default
default_stages = [s for s in stages if s not in closed]
sel_stages = st.sidebar.multiselect('Sales Stage', stages, default=default_stages)
if sel_stages:
    df = df[df['Stage'].isin(sel_stages)]
# Region: Brazil / Hispanic
regions = ['Todos', 'Brazil', 'Hispanic']
sel_region = st.sidebar.selectbox('Region', regions)
if sel_region != 'Todos' and 'Sub Territory' in df.columns:
    df = df[df['Sub Territory'].astype(str).str.contains(sel_region, case=False, na=False)]



# 9) Filtros adicionais personalizados
# --- Converter dias em número, evitar erro de bins
if 'Days Since Next Steps Modified' in df.columns:
    df['Days Since Next Steps Modified'] = pd.to_numeric(
        df['Days Since Next Steps Modified'], errors='coerce'
    )
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
    labels = ['<=7 dias', '8-14 dias', '15-30 dias', '>30 dias']
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
edu_choice = st.sidebar.radio('Filtro EDU', ['All', 'EDU', 'Others'], index=0)
if edu_choice == 'EDU':
    df = enum_df[enum_df['Sub Territory'].str.contains('EDU', case=False, na=False)]
elif edu_choice == 'Others':
    df = enum_df[~enum_df['Sub Territory'].str.contains('EDU', case=False, na=False)]
else:
    df = enum_df

# Totais atualizados após todos os filtros (incluindo EDU)
total_pipeline = df[df['Stage'].isin([
    '03 - Opportunity Qualification','04 - Circle of Influence',
    '05 - Solution Definition and Validation',
    '06 - Customer Commit'
])]['Total New ASV'].sum()
total_won = df[df['Stage'].isin(['07 - Execute to Close', 'Closed - Booked'])]['Total New ASV'].sum()
st.subheader(f"Total Pipeline: {total_pipeline:,.2f}   Total Won: {total_won:,.2f}")
# Exibir filtros aplicados (excluindo Sales Stage)
applied_filters = []
if sel_member != 'Todos': applied_filters.append(f"Sales Team Member: {sel_member}")
if sel_region != 'Todos': applied_filters.append(f"Region: {sel_region}")
# Filtros adicionais personalizados
if 'sel_fq' in locals() and sel_fq != 'Todos': applied_filters.append(f"Fiscal Quarter: {sel_fq}")
if 'sel_fc' in locals() and sel_fc != 'Todos': applied_filters.append(f"Forecast Indicator: {sel_fc}")
if 'sel_drid' in locals() and sel_drid != 'Todos': applied_filters.append(f"Deal Registration ID: {sel_drid}")
if 'sel_dg' in locals() and sel_dg != 'Todos': applied_filters.append(f"Dias desde Next Steps: {sel_dg}")
if 'sel_lpt' in locals() and sel_lpt != 'Todos': applied_filters.append(f"Licensing Program Type: {sel_lpt}")
if 'sel_op' in locals() and sel_op != 'Todos': applied_filters.append(f"Opportunity: {sel_op}")
if 'sel_an' in locals() and sel_an != 'Todos': applied_filters.append(f"Account Name: {sel_an}")
if 'sel_state' in locals() and sel_state != 'Todos': applied_filters.append(f"State/Province: {sel_state}")
# Filtro EDU
if edu_choice != 'All': applied_filters.append(f"Filtro EDU: {edu_choice}")
if applied_filters:
    st.markdown("**Filtros aplicados:** " + " | ".join(applied_filters))
    # Download filtered data (CSV)
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        '⬇️ Download Filtered Data (CSV)',
        csv_data,
        file_name=f'pipeline_{file.replace(".csv","")}.csv',
        mime='text/csv'
    )

# Helper to download plot as HTML
def download_html(fig, name):
    buf = io.StringIO()
    fig.write_html(buf, include_plotlyjs='cdn')
    st.download_button(f'⬇️ Download {name} (HTML)', buf.getvalue(), file_name=f'{name}.html', mime='text/html')

# 10) Pipeline por Fase
st.header('🔍 Pipeline por Fase')
order = [
    '02 - Prospect', '03 - Opportunity Qualification', '04 - Circle of Influence','05 - Solution Definition and Validation',
    '06 - Customer Commit', '07 - Execute to Close', 'Closed - Booked'
]

phase = df[df['Stage'].isin(order)].groupby('Stage')['Total New ASV'].sum().reindex(order).reset_index()
fig = px.bar(
    phase, x='Total New ASV', y='Stage', orientation='h', template='plotly_dark',
    text='Total New ASV', color='Stage', color_discrete_sequence=px.colors.qualitative.Vivid
)
fig.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
st.plotly_chart(fig, use_container_width=True, key='pipeline_stage')
download_html(fig, 'pipeline_by_stage')

# 11) Pipeline Semanal
st.header('📈 Pipeline Semanal')
dfw = df.dropna(subset=['Close Date']).copy()
dfw['Week'] = dfw['Close Date'].dt.to_period('W').dt.to_timestamp()
weekly = dfw.groupby('Week')['Total New ASV'].sum().reset_index()
fig2 = px.line(weekly, x='Week', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig2.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig2, use_container_width=True, key='pipeline_weekly')
download_html(fig2, 'pipeline_weekly')

# 12) Pipeline Mensal
st.header('📆 Pipeline Mensal')
mon = dfw.copy()
mon['Month'] = mon['Close Date'].dt.to_period('M').dt.to_timestamp()
monthly = mon.groupby('Month')['Total New ASV'].sum().reset_index()
fig3 = px.line(monthly, x='Month', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig3.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig3, use_container_width=True, key='pipeline_monthly')
download_html(fig3, 'pipeline_monthly')

# 13) Ranking de Vendedores
st.header('🏆 Ranking de Vendedores')
r = df.groupby('Sales Team Member')['Total New ASV'].sum().reset_index().sort_values('Total New ASV', ascending=False)
r['Rank'] = range(1, len(r) + 1)
r['Total New ASV'] = r['Total New ASV'].map('${:,.2f}'.format)
st.table(r[['Rank','Sales Team Member','Total New ASV']])

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
        download_html(fig, title.replace(' ', '_').lower())

# 15) Dados Brutos e ficha detalhada e ficha detalhada
st.header('📋 Dados Brutos')
disp = df.copy()
gb = GridOptionsBuilder.from_dataframe(disp)
gb.configure_default_column(cellStyle={'color':'white','backgroundColor':'#000000'})
numeric_cols = disp.select_dtypes(include=[np.number]).columns.tolist()
us_format = JsCode("function(params){return params.value!=null?params.value.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}):''}")
for col in numeric_cols:
    gb.configure_column(
        col,
        type=['numericColumn','numberColumnFilter'],
        cellStyle={'textAlign':'right','color':'white','backgroundColor':'#000000'},
        cellRenderer=us_format
    )
gb.configure_selection(selection_mode='single',use_checkbox=True)
grid_resp = AgGrid(
    disp,
    gridOptions=gb.build(),
    theme='streamlit-dark',
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    allow_unsafe_jscode=True,
    height=500
)
# Download displayed raw data (filtered)
csv_disp = disp.to_csv(index=False).encode('utf-8')
st.download_button(
    '⬇️ Download Displayed Raw Data (CSV)',
    data=csv_disp,
    file_name='displayed_raw_data.csv',
    mime='text/csv'
)
sel = grid_resp['selected_rows']
if isinstance(sel, pd.DataFrame):
    sel_list = sel.to_dict('records')
else:
    sel_list = sel or []
if sel_list:
    rec = sel_list[0]
    st.markdown('---')
    with st.expander(f"🗂 Ficha: {rec.get('Opportunity','')}",expanded=True):
        highlights=['Stage','Total New ASV','Close Date','Total TSV','Original Close Date','Deal Registration ID','Owner','Total DMe Est HASV','Sales Team Member']
        cols=st.columns(3)
        for i,k in enumerate(highlights):
            with cols[i%3]:
                st.markdown(f"<span style='color:#FFD700'><strong>{k}:</strong> {rec.get(k,'')}</span>",unsafe_allow_html=True)
        st.markdown('<hr/>',unsafe_allow_html=True)
        items=[(k,v) for k,v in rec.items() if k not in highlights+['Next Steps','Forecast Notes']]
        cols2=st.columns(3)
        for i,(k,v) in enumerate(items):
            with cols2[i%3]:
                st.markdown(f"**{k}:** {v}")
        st.markdown('<hr/>',unsafe_allow_html=True)
        st.markdown("<span style='color:#FFD700'><strong>Next Steps:</strong></span>",unsafe_allow_html=True)
        st.write(rec.get('Next Steps',''))
        st.markdown('<hr/>',unsafe_allow_html=True)
        st.markdown("<span style='color:#FFD700'><strong>Forecast Notes:</strong></span>",unsafe_allow_html=True)
        st.write(rec.get('Forecast Notes',''))

# 16) Commit Deals
# --- bloco novo: seleção de Committed Deals (mantém #15 intacto)
st.markdown('---')
st.header('✅ Seleção de Committed Deals')

# monta apenas as colunas de interesse
commit_disp = df[[
    'Deal Registration ID',
    'Opportunity',
    'Sales Team Member',
    'Stage',
    'Close Date',
    'Total New ASV',
    'Next Steps'
]].copy()

# ← INSIRA AQUI o truncamento de Next Steps
commit_disp['Next Steps'] = (
    commit_disp['Next Steps']
    .astype(str)
    .str.slice(0, 50)
)


# configura AgGrid para seleção múltipla
commit_gb = GridOptionsBuilder.from_dataframe(commit_disp)
commit_gb.configure_default_column(cellStyle={'color':'white','backgroundColor':'#000000'})
# formata numéricos
for col in ['Total New ASV']:
    commit_gb.configure_column(
        col,
        type=['numericColumn','numberColumnFilter'],
        cellStyle={'textAlign':'right','color':'white','backgroundColor':'#000000'},
        cellRenderer=us_format
    )
# habilita múltipla seleção
commit_gb.configure_selection(selection_mode='multiple', use_checkbox=True)

# exibe grid
commit_resp = AgGrid(
    commit_disp,
    gridOptions=commit_gb.build(),
    theme='streamlit-dark',
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    allow_unsafe_jscode=True,
    height=300
)

# captura seleção (tratando DataFrame ou lista)
sel_raw = commit_resp['selected_rows']
if isinstance(sel_raw, pd.DataFrame):
    sel_list = sel_raw.to_dict('records')
else:
    sel_list = sel_raw or []

if sel_list:
    commit_df = pd.DataFrame(sel_list)
else:
    commit_df = pd.DataFrame(columns=commit_disp.columns)


# mostra Committed Deals
st.subheader('📋 Committed Deals')
# formata Total New ASV em US e alinha à direita
styled = (
    commit_df
    .style
    .format({'Total New ASV': '${:,.2f}'})
    .set_properties(subset=['Total New ASV'], **{'text-align': 'right'})
)
st.dataframe(styled, use_container_width=True)


# botão de download
csv_commit = commit_df.to_csv(index=False).encode('utf-8')
st.download_button(
    '⬇️ Download Committed Deals (CSV)',
    data=csv_commit,
    file_name='committed_deals.csv',
    mime='text/csv'
)

