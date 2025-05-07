import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Configuração da página
st.set_page_config(page_title="Dashboard Pipeline LATAM", layout="wide")
st.title("📊 Dashboard Pipeline LATAM")

# Diretório atual para CSVs
dir_path = os.getcwd()

# Função para listar CSVs (cache para performance)
@st.cache_data
def list_csv_files():
    return sorted([f for f in os.listdir(dir_path) if f.lower().endswith('.csv')])

# Sidebar: seleção de arquivo
st.sidebar.header('📂 Selecione o arquivo CSV')
csv_files = list_csv_files()
selected = st.sidebar.selectbox('Arquivos disponíveis:', [''] + csv_files)
if not selected:
    st.info('Selecione um arquivo CSV para continuar.')
    st.stop()

# Carrega e sanitiza dados
@st.cache_data(ttl=600)
def load_data(f):
    df = pd.read_csv(os.path.join(dir_path, f))
    df.columns = df.columns.str.strip()
    df['Sales Team Member'] = df.get('Sales Team Member', df.get('Owner', '')).astype(str).str.strip()
    df['Stage'] = df['Stage'].astype(str).str.strip()
    df['Close Date'] = pd.to_datetime(df['Close Date'], errors='coerce')
    if 'Created Date' in df.columns:
        df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
    df['Total New ASV'] = (
        df['Total New ASV'].astype(str)
          .str.replace(r"[\$,]", '', regex=True)
          .astype(float)
    )
    return df

# Carrega dados
df = load_data(selected)

# Filtros na sidebar
st.sidebar.header('🔍 Filtros')
# Sales Team Member
o_members = ['Todos'] + sorted(df['Sales Team Member'].unique())
sel_member = st.sidebar.selectbox('Sales Team Member:', o_members)
if sel_member != 'Todos':
    df = df[df['Sales Team Member'] == sel_member]

# Sales Stage multi-seleção
st.sidebar.subheader('Sales Stage')
stages = sorted(df['Stage'].unique())
sel_stages = st.sidebar.multiselect('Sales Stage:', stages, default=stages)
if sel_stages:
    df = df[df['Stage'].isin(sel_stages)]

# Forecast Indicator (fora dos filtros adicionais)
if 'Forecast Indicator' in df.columns:
    fi_opts = sorted(df['Forecast Indicator'].dropna().unique())
    sel_fi = st.sidebar.selectbox('Forecast Indicator:', ['Todos'] + fi_opts)
    if sel_fi and sel_fi != 'Todos':
        df = df[df['Forecast Indicator'] == sel_fi]

# Sub Territory (fora dos filtros adicionais)
if 'Sub Territory' in df.columns:
    st.sidebar.subheader('Sub Territory')
    st_sub = sorted(df['Sub Territory'].dropna().unique())
    sel_sub = st.sidebar.selectbox('Sub Territory:', ['Todos'] + st_sub)
    if sel_sub and sel_sub != 'Todos':
        df = df[df['Sub Territory'] == sel_sub]

# Filtros adicionais agrupados
with st.sidebar.expander('Filtros adicionais'):
    ignore = [
        'Sales Team Member', 'Stage', 'Close Date', 'Total New ASV',
        'Record Owner', 'Currency', 'Opportunity ID',
        'Opportunity Currency', 'Clari Score', 'Created Date',
        'Forecast', 'Forecast Notes', 'ProbByClose',
        'Account Name', 'Account Name.1',
        'Days Since Next Steps Modified', 'Next Steps',
        'Renewal Bookings', 'Total DMe Est HASV',
        'Accept into Sales Pipeline', 'Accept into Sales Pipeline.1',
        'Total TSV', 'Total Attrition', 'Close Reason Detail'
    ]
    for col in [c for c in df.columns if c not in ignore]:
        opts = sorted(df[col].dropna().unique().tolist())
        sel = st.multiselect(col, opts, key=col)
        if sel:
            df = df[df[col].isin(sel)]

# Totais principais
pipeline_stages = [
    '03 - Opportunity Qualification',
    '05 - Solution Definition and Validation',
    '06 - Customer Commit'
]
won_stages = [
    '07 - Execute to Close',
    'Closed - Booked'
]
pipeline_total = df[df['Stage'].isin(pipeline_stages)]['Total New ASV'].sum()
won_total = df[df['Stage'].isin(won_stages)]['Total New ASV'].sum()
st.subheader(f"Total Pipeline: {pipeline_total:,.2f}   Total Won: {won_total:,.2f}")

# 1) Pipeline por Fase
st.header('🔍 Pipeline por Fase')
order = [
    '02 - Prospect',
    '03 - Opportunity Qualification',
    '05 - Solution Definition and Validation',
    '06 - Customer Commit',
    '07 - Execute to Close',
    'Closed - Booked'
]
data = df[df['Stage'].isin(order)].groupby('Stage', as_index=False)['Total New ASV'].sum()
data['Stage'] = pd.Categorical(data['Stage'], categories=order, ordered=True)
fig1 = px.bar(
    data, x='Total New ASV', y='Stage', orientation='h',
    color='Stage', color_discrete_sequence=px.colors.qualitative.Vivid,
    template='plotly_dark', text='Total New ASV'
)
fig1.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
st.plotly_chart(fig1, use_container_width=True, height=400)

# 2) Pipeline Semanal (data de fechamento)
tmp = df.dropna(subset=['Close Date']).copy()
tmp['Week'] = tmp['Close Date'].dt.to_period('W').dt.start_time
weekly = tmp.groupby('Week')['Total New ASV'].sum().reset_index()
fig2 = px.line(
    weekly, x='Week', y='Total New ASV', markers=True,
    template='plotly_dark', text='Total New ASV'
)
fig2.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig2, use_container_width=True, height=350)

# 3) Pipeline Created (AF 2025)
if 'Created Date' in df.columns:
    st.header('🆕 Pipeline Created (AF 2025)')
    start = pd.Timestamp('2024-12-01')
    end = pd.Timestamp('2025-11-30')
    tmpc = df.dropna(subset=['Created Date']).copy()
    tmpc = tmpc[(tmpc['Created Date'] >= start) & (tmpc['Created Date'] <= end)]
    tmpc['Week'] = tmpc['Created Date'].dt.to_period('W').dt.start_time
    created = tmpc.groupby('Week')['Total New ASV'].sum().reset_index()
    figc = px.line(
        created, x='Week', y='Total New ASV', markers=True,
        template='plotly_dark', text='Total New ASV'
    )
    figc.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
    st.plotly_chart(figc, use_container_width=True, height=350)

# 4) Ranking de Membros da Equipe
st.header('🏆 Ranking de Membros da Equipe')
r = (df.groupby('Sales Team Member', as_index=False)
       ['Total New ASV'].sum()
       .sort_values('Total New ASV', ascending=False)
     )
r['Rank'] = range(1, len(r) + 1)
r['Total New ASV'] = r['Total New ASV'].map('${:,.2f}'.format)
r = r[['Rank', 'Sales Team Member', 'Total New ASV']]
r = r.reset_index(drop=True)
st.table(r)

# 5) Forecast Indicator
st.header('📊 Forecast Indicator')
if 'Forecast Indicator' in df.columns:
    fc = df.groupby('Forecast Indicator', as_index=False)['Total New ASV'].sum()
    fig3 = px.bar(
        fc, x='Forecast Indicator', y='Total New ASV',
        color='Forecast Indicator', color_discrete_sequence=px.colors.qualitative.Vivid,
        template='plotly_dark', text='Total New ASV'
    )
    fig3.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
    st.plotly_chart(fig3, use_container_width=True, height=350)
else:
    st.info("Coluna 'Forecast Indicator' ausente.")

# 6) Licensing Program Type
st.header('📊 Licensing Program Type')
if 'Licensing Program Type' in df.columns:
    lt = df.groupby('Licensing Program Type', as_index=False)['Total New ASV'].sum()
    fig4 = px.bar(
        lt, x='Licensing Program Type', y='Total New ASV',
        color='Licensing Program Type', color_discrete_sequence=px.colors.qualitative.Vivid,
        template='plotly_dark', text='Total New ASV'
    )
    fig4.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
    st.plotly_chart(fig4, use_container_width=True, height=350)
else:
    st.info("Coluna 'Licensing Program Type' ausente.")

# 7) Licensing Program
st.header('📊 Licensing Program')
if 'Licensing Program' in df.columns:
    lp = df.groupby('Licensing Program', as_index=False)['Total New ASV'].sum()
    fig5 = px.bar(
        lp, x='Licensing Program', y='Total New ASV',
        color='Licensing Program', color_discrete_sequence=px.colors.qualitative.Vivid,
        template='plotly_dark', text='Total New ASV'
    )
    fig5.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
    st.plotly_chart(fig5, use_container_width=True, height=350)
else:
    st.info("Coluna 'Licensing Program' ausente.")

# 8) Major OLPG1
st.header('📊 Major OLPG1')
if 'Major OLPG1' in df.columns:
    mo = df.groupby('Major OLPG1', as_index=False)['Total New ASV'].sum()
    fig6 = px.bar(
        mo, x='Major OLPG1', y='Total New ASV',
        color='Major OLPG1', color_discrete_sequence=px.colors.qualitative.Vivid,
        template='plotly_dark', text='Total New ASV'
    )
    fig6.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
    st.plotly_chart(fig6, use_container_width=True, height=350)
else:
    st.info("Coluna 'Major OLPG1' ausente.")

# Última seção: Dados Brutos
st.header('📋 Dados Brutos')
disp = df.sort_values('Total New ASV', ascending=False).copy()
disp['Total New ASV'] = disp['Total New ASV'].map(lambda x: f"{x:,.2f}")
st.dataframe(disp)
