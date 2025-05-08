import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import io
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1) Configurações iniciais
dir = os.getcwd()
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
title = "📊 Dashboard Pipeline LATAM"
st.title(title)

# 3) Lista de CSVs disponíveis
@st.cache_data
def list_csv_files():
    return sorted([f for f in os.listdir(dir) if f.lower().endswith('.csv')])

# 4) Função de carregamento e sanitização de dados
def load_data(path):
    df = pd.read_csv(os.path.join(dir, path))
    df.columns = df.columns.str.strip()
    df['Opportunity'] = df.get('Opportunity', df.get('Opportunity ID', ''))
    df['Sales Team Member'] = df.get('Sales Team Member', df.get('Owner', '')).astype(str).str.strip()
    df['Stage'] = df['Stage'].astype(str).str.strip()
    df['Close Date'] = pd.to_datetime(df['Close Date'], errors='coerce')
    df['Total New ASV'] = df['Total New ASV'].astype(str).str.replace(r"[\$,]", '', regex=True).astype(float)
    for col in ['Renewal Bookings','Total DMe Est HASV','Total Attrition','Total TSV','Total Renewal ASV']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r"[\$,]", '', regex=True).astype(float)
    if 'Sub Territory' in df.columns:
        df['Region'] = df['Sub Territory'].astype(str).apply(lambda x: 'Hispanic' if 'Hispanic' in x else ('Brazil' if 'Brazil' in x else 'Other'))
    else:
        df['Region'] = 'Other'
    return df

# 5) Seleção de CSV
st.sidebar.header('📂 Selecione o CSV')
file = st.sidebar.selectbox('Arquivo:', [''] + list_csv_files())
if not file:
    st.info('Selecione um CSV para continuar')
    st.stop()

df = load_data(file)

# 6) Filtros Básicos
st.sidebar.header('🔍 Filtros')
# Sales Team Member
members = ['Todos'] + sorted(df['Sales Team Member'].unique())
sel_member = st.sidebar.selectbox('Sales Team Member', members)
if sel_member != 'Todos': df = df[df['Sales Team Member'] == sel_member]
# Sales Stage
stages = sorted(df['Stage'].unique())
closed = ['Closed - Clean Up','Closed - Lost']
default = [s for s in stages if s not in closed]
sel_stages = st.sidebar.multiselect('Sales Stage', stages, default=default)
if sel_stages: df = df[df['Stage'].isin(sel_stages)]
# Region
regions = ['Todos','Brazil','Hispanic']
sel_region = st.sidebar.selectbox('Region', regions)
if sel_region != 'Todos': df = df[df['Sub Territory'].astype(str).str.contains(sel_region, case=False, na=False)]

# 7) Filtros Adicionais
if 'Days Since Next Steps Modified' in df:
    df['Days Since Next Steps Modified'] = pd.to_numeric(df['Days Since Next Steps Modified'], errors='coerce')
st.sidebar.header('🔧 Filtros adicionais')
if 'Fiscal Quarter' in df:
    sel_fq = st.sidebar.selectbox('Fiscal Quarter',['Todos']+sorted(df['Fiscal Quarter'].dropna().unique()))
    if sel_fq!='Todos': df=df[df['Fiscal Quarter']==sel_fq]
if 'Forecast Indicator' in df:
    sel_fc = st.sidebar.selectbox('Forecast Indicator',['Todos']+sorted(df['Forecast Indicator'].dropna().unique()))
    if sel_fc!='Todos': df=df[df['Forecast Indicator']==sel_fc]
if 'Deal Registration ID' in df:
    sel_drid = st.sidebar.selectbox('Deal Registration ID',['Todos']+sorted(df['Deal Registration ID'].dropna().unique()))
    if sel_drid!='Todos': df=df[df['Deal Registration ID']==sel_drid]
if 'Days Since Next Steps Modified' in df:
    labels=['<=7 dias','8-14 dias','15-30 dias','>30 dias']
    df['DaysGroup']=pd.cut(df['Days Since Next Steps Modified'],bins=[0,7,14,30,float('inf')],labels=labels)
    sel_dg=st.sidebar.selectbox('Dias desde Next Steps',['Todos']+labels)
    if sel_dg!='Todos': df=df[df['DaysGroup']==sel_dg]
if 'Licensing Program Type' in df:
    sel_lpt=st.sidebar.selectbox('Licensing Program Type',['Todos']+sorted(df['Licensing Program Type'].dropna().unique()))
    if sel_lpt!='Todos': df=df[df['Licensing Program Type']==sel_lpt]
if 'Opportunity' in df:
    sel_op=st.sidebar.selectbox('Opportunity',['Todos']+sorted(df['Opportunity'].dropna().unique()))
    if sel_op!='Todos': df=df[df['Opportunity']==sel_op]
if 'Account Name' in df:
    sel_an=st.sidebar.selectbox('Account Name',['Todos']+sorted(df['Account Name'].dropna().unique()))
    if sel_an!='Todos': df=df[df['Account Name']==sel_an]
if 'Account Address: State/Province' in df:
    sel_state=st.sidebar.selectbox('State/Province',['Todos']+sorted(df['Account Address: State/Province'].dropna().unique()))
    if sel_state!='Todos': df=df[df['Account Address: State/Province']==sel_state]
enum_df=df.copy()
edu_choice=st.sidebar.radio('Filtro EDU',['All','EDU','Others'],index=0)
if edu_choice=='EDU': df=enum_df[enum_df['Sub Territory'].str.contains('EDU',case=False,na=False)]
elif edu_choice=='Others': df=enum_df[~enum_df['Sub Territory'].str.contains('EDU',case=False,na=False)]
else: df=enum_df

# 8) Totais
total_pipe = df[df['Stage'].isin(['03 - Opportunity Qualification','04 - Circle of Influence','05 - Solution Definition and Validation','06 - Customer Commit'])]['Total New ASV'].sum()
total_won = df[df['Stage'].isin(['07 - Execute to Close','Closed - Booked'])]['Total New ASV'].sum()
st.subheader(f"Total Pipeline: {total_pipe:,.2f}   Total Won: {total_won:,.2f}")

# 9) Exibir filtros aplicados
applied=[]
if sel_member!='Todos': applied.append(f"Sales Team Member: {sel_member}")
if sel_region!='Todos': applied.append(f"Region: {sel_region}")
for var,name in [('sel_fq','Fiscal Quarter'),('sel_fc','Forecast Indicator'),('sel_drid','Deal Registration ID'),('sel_dg','Dias desde Next Steps'),('sel_lpt','Licensing Program Type'),('sel_op','Opportunity'),('sel_an','Account Name'),('sel_state','State/Province')]:
    if var in locals() and locals()[var] not in ['Todos','All']: applied.append(f"{name}: {locals()[var]}")
if edu_choice!='All': applied.append(f"Filtro EDU: {edu_choice}")
if applied: st.markdown("**Filtros aplicados:** " + " | ".join(applied))

# Funções de exportação
buffer = io.BytesIO()
# Usar openpyxl para evitar ausência do xlsxwriter
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name='Dados')
buffer.seek(0)
st.download_button(
    '⬇️ Baixar dados filtrados (Excel)',
    data=buffer,
    file_name=f'pipeline_{file.split('.csv')[0]}.xlsx',
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)

def export_plot(fig, name):
    img = fig.to_image(format='png')
    st.download_button(
        f'⬇️ Baixar {name} (PNG)',
        data=img,
        file_name=f'{name}.png',
        mime='image/png'
)

# 10) Pipeline por Fase
order=['02 - Prospect','03 - Opportunity Qualification','04 - Circle of Influence','05 - Solution Definition and Validation','06 - Customer Commit','07 - Execute to Close','Closed - Booked']
phase=df[df['Stage'].isin(order)].groupby('Stage')['Total New ASV'].sum().reindex(order).reset_index()
fig_phase=px.bar(phase, x='Total New ASV', y='Stage', orientation='h', template='plotly_dark', text='Total New ASV')
fig_phase.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
st.header('🔍 Pipeline por Fase')
st.plotly_chart(fig_phase, use_container_width=True)
export_plot(fig_phase,'pipeline_por_fase')

# 11) Pipeline Semanal
dfw=df.dropna(subset=['Close Date']).copy()
dfw['Week']=dfw['Close Date'].dt.to_period('W').dt.to_timestamp()
weekly=dfw.groupby('Week')['Total New ASV'].sum().reset_index()
fig_weekly=px.line(weekly, x='Week', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig_weekly.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.header('📈 Pipeline Semanal')
st.plotly_chart(fig_weekly, use_container_width=True)
export_plot(fig_weekly,'pipeline_semanal')

# 12) Pipeline Mensal
mon=dfw.copy()
mon['Month']=mon['Close Date'].dt.to_period('M').dt.to_timestamp()
monthly=mon.groupby('Month')['Total New ASV'].sum().reset_index()
fig_monthly=px.line(monthly, x='Month', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig_monthly.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.header('📆 Pipeline Mensal')
st.plotly_chart(fig_monthly, use_container_width=True)
export_plot(fig_monthly,'pipeline_mensal')

# 13) Ranking de Vendedores
rank_df=df.groupby('Sales Team Member')['Total New ASV'].sum().reset_index().sort_values('Total New ASV',ascending=False)
rank_df['Rank']=range(1,len(rank_df)+1)
rank_df['Total New ASV']=rank_df['Total New ASV'].map('${:,.2f}'.format)
st.header('🏆 Ranking de Vendedores')
st.table(rank_df[['Rank','Sales Team Member','Total New ASV']])

# 14) Gráficos adicionais
extras=[('Forecast Indicator','Pipeline por Forecast Indicator'),('Licensing Program Type','Pipeline por Licensing Program Type'),('Licensing Program','Pipeline por Licensing Program'),('Major OLPG1','Pipeline por Major OLPG1')]
for col,title in extras:
    if col in df:
        dcol=df.groupby(col)['Total New ASV'].sum().reset_index()
        fig_extra=px.bar(dcol, x=col, y='Total New ASV', color=col, template='plotly_dark', text='Total New ASV')
        fig_extra.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
        st.header(f'📊 {title}')
        st.plotly_chart(fig_extra, use_container_width=True)
        export_plot(fig_extra,title.lower().replace(' ','_'))

# 15) Dados Brutos e Ficha
st.header('📋 Dados Brutos')
disp=df.copy()
gb=GridOptionsBuilder.from_dataframe(disp)
gb.configure_default_column(cellStyle={'color':'white','backgroundColor':'#000000'})
numeric=disp.select_dtypes(include=[np.number]).columns.tolist()
js=JsCode("function(params){return params.value!=null?params.value.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}):''}")
for col in numeric:
    gb.configure_column(col,type=['numericColumn','numberColumnFilter'],cellStyle={'textAlign':'right','color':'white','backgroundColor':'#000000'},cellRenderer=js)
gb.configure_selection(selection_mode='single',use_checkbox=True)
gr=AgGrid(disp,gridOptions=gb.build(),theme='streamlit-dark',update_mode=GridUpdateMode.SELECTION_CHANGED,allow_unsafe_jscode=True,height=500)
sel=gr['selected_rows'] if isinstance(gr['selected_rows'], list) else []
if sel:
    rec=sel[0]
    st.markdown('---')
    with st.expander(f"🗂 Ficha: {rec.get('Opportunity','')}",expanded=True):
        hl=['Stage','Total New ASV','Close Date','Total TSV','Original Close Date','Deal Registration ID','Owner','Total DMe Est HASV','Sales Team Member']
        cols=st.columns(3)
        for i,k in enumerate(hl):
            with cols[i%3]: st.markdown(f"<span style='color:#FFD700'><strong>{k}:</strong> {rec.get(k,'')}</span>",unsafe_allow_html=True)
        st.markdown('<hr/>',unsafe_allow_html=True)
        items=[(k,v) for k,v in rec.items() if k not in hl+['Next Steps','Forecast Notes']]
        cols2=st.columns(3)
        for i,(k,v) in enumerate(items):
            with cols2[i%3]: st.markdown(f"**{k}:** {v}")
        st.markdown('<hr/>',unsafe_allow_html=True)
        st.markdown("<span style='color:#FFD700'><strong>Next Steps:</strong></span>",unsafe_allow_html=True)
        st.write(rec.get('Next Steps',''))
        st.markdown('<hr/>',unsafe_allow_html=True)
        st.markdown("<span style='color:#FFD700'><strong>Forecast Notes:</strong></span>",unsafe_allow_html=True)
        st.write(rec.get('Forecast Notes',''))
