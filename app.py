import streamlit as st
import pandas as pd
import numpy as np
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

# 2) Verificar suporte a exportação de imagens
try:
    import kaleido
    _IMG_SUPPORT = True
except ImportError:
    _IMG_SUPPORT = False

# 3) Título
st.title("📊 Dashboard Pipeline LATAM")

# 4) Caminho dos CSVs e listagem
dir = os.getcwd()
@st.cache_data
def list_csv_files():
    return sorted([f for f in os.listdir(dir) if f.lower().endswith('.csv')])

# 5) Função de carregamento e sanitização
def load_data(path):
    df = pd.read_csv(os.path.join(dir, path))
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
st.sidebar.header('📂 Selecione o CSV')
file = st.sidebar.selectbox('Arquivo:', [''] + list_csv_files())
if not file:
    st.info('Selecione um CSV para continuar')
    st.stop()

df = load_data(file)

# 7) Filtros básicos
st.sidebar.header('🔍 Filtros')
tmembers = ['Todos'] + sorted(df['Sales Team Member'].unique())
sel_member = st.sidebar.selectbox('Sales Team Member', tmembers)
if sel_member != 'Todos': df = df[df['Sales Team Member'] == sel_member]
stages = sorted(df['Stage'].unique())
closed = ['Closed - Clean Up', 'Closed - Lost']
default_stages = [s for s in stages if s not in closed]
sel_stages = st.sidebar.multiselect('Sales Stage', stages, default=default_stages)
if sel_stages: df = df[df['Stage'].isin(sel_stages)]
regions = ['Todos', 'Brazil', 'Hispanic']
sel_region = st.sidebar.selectbox('Region', regions)
if sel_region != 'Todos': df = df[df['Sub Territory'].astype(str).str.contains(sel_region, case=False, na=False)]

# 8) Filtros adicionais personalizados
if 'Days Since Next Steps Modified' in df.columns:
    df['Days Since Next Steps Modified'] = pd.to_numeric(df['Days Since Next Steps Modified'], errors='coerce')
st.sidebar.header('🔧 Filtros adicionais')
for key,label in [
    ('Fiscal Quarter','Fiscal Quarter'),
    ('Forecast Indicator','Forecast Indicator'),
    ('Deal Registration ID','Deal Registration ID'),
    ('Licensing Program Type','Licensing Program Type'),
    ('Opportunity','Opportunity'),
    ('Account Name','Account Name'),
    ('Account Address: State/Province','State/Province')
]:
    if key in df.columns:
        sel = st.sidebar.selectbox(label, ['Todos'] + sorted(df[key].dropna().unique()))
        if sel != 'Todos': df = df[df[key] == sel]
if 'Days Since Next Steps Modified' in df.columns:
    labels = ['<=7 dias','8-14 dias','15-30 dias','>30 dias']
    df['DaysGroup'] = pd.cut(df['Days Since Next Steps Modified'], bins=[0,7,14,30,float('inf')], labels=labels)
    sel_dg = st.sidebar.selectbox('Dias desde Next Steps', ['Todos'] + labels)
    if sel_dg != 'Todos': df = df[df['DaysGroup'] == sel_dg]
enum_df = df.copy()
edu_choice = st.sidebar.radio('Filtro EDU', ['All','EDU','Others'], index=0)
if edu_choice == 'EDU': df = enum_df[enum_df['Sub Territory'].str.contains('EDU', case=False, na=False)]
elif edu_choice == 'Others': df = enum_df[~enum_df['Sub Territory'].str.contains('EDU', case=False, na=False)]

# 9) Totais
total_pipeline = df[df['Stage'].isin([
    '03 - Opportunity Qualification','04 - Circle of Influence',
    '05 - Solution Definition and Validation','06 - Customer Commit'
])]['Total New ASV'].sum()
total_won = df[df['Stage'].isin(['07 - Execute to Close','Closed - Booked'])]['Total New ASV'].sum()
st.subheader(f"Total Pipeline: {total_pipeline:,.2f}   Total Won: {total_won:,.2f}")

# 10) Exibir filtros aplicados
applied = []
if sel_member!='Todos': applied.append(f"Sales Team Member: {sel_member}")
if sel_region!='Todos': applied.append(f"Region: {sel_region}")
for var,label in [('sel_fq','Fiscal Quarter'),('sel_fc','Forecast Indicator'),('sel_drid','Deal Registration ID'),('sel_dg','Dias desde Next Steps'),('sel_lpt','Licensing Program Type'),('sel_op','Opportunity'),('sel_an','Account Name'),('sel_state','State/Province')]:
    if var in locals() and locals()[var] not in ['Todos','All']:
        applied.append(f"{label}: {locals()[var]}")
if edu_choice!='All': applied.append(f"Filtro EDU: {edu_choice}")
if applied: st.markdown("**Filtros aplicados:** " + " | ".join(applied))

# 11) Exportação de dados (CSV)
csv_data = df.to_csv(index=False).encode('utf-8')
st.download_button('⬇️ Baixar dados filtrados (CSV)', csv_data, file_name=f'pipeline_{file.split(".csv")[0]}.csv', mime='text/csv')

# Função para exportar gráfico como PNG
def export_plot(fig, name):
    if not _IMG_SUPPORT:
        st.warning('Instale o pacote kaleido para habilitar download de imagens')
        return
    try:
        img = fig.to_image(format='png')
        st.download_button(f'⬇️ Baixar {name} (PNG)', img, file_name=f'{name}.png', mime='image/png')
    except Exception as e:
        st.error(f'Erro ao gerar imagem: {e}')

# 12) Pipeline por Fase
st.header('🔍 Pipeline por Fase')
order=[
    '02 - Prospect','03 - Opportunity Qualification','04 - Circle of Influence','05 - Solution Definition and Validation',
    '06 - Customer Commit','07 - Execute to Close','Closed - Booked'
]
phase=df[df['Stage'].isin(order)].groupby('Stage')['Total New ASV'].sum().reindex(order).reset_index()
fig=px.bar(phase, x='Total New ASV', y='Stage', orientation='h', template='plotly_dark', text='Total New ASV', color='Stage', color_discrete_sequence=px.colors.qualitative.Vivid)
fig.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
st.plotly_chart(fig, use_container_width=True)
export_plot(fig,'pipeline_por_fase')

# 13) Pipeline Semanal
st.header('📈 Pipeline Semanal')
dfw=df.dropna(subset=['Close Date']).copy()
dfw['Week']=dfw['Close Date'].dt.to_period('W').dt.to_timestamp()
weekly=dfw.groupby('Week')['Total New ASV'].sum().reset_index()
fig2=px.line(weekly, x='Week', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig2.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig2, use_container_width=True)
export_plot(fig2,'pipeline_semanal')

# 14) Pipeline Mensal
st.header('📆 Pipeline Mensal')
mon=dfw.copy()
mon['Month']=mon['Close Date'].dt.to_period('M').dt.to_timestamp()
monthly=mon.groupby('Month')['Total New ASV'].sum().reset_index()
fig3=px.line(monthly, x='Month', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig3.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig3, use_container_width=True)
export_plot(fig3,'pipeline_mensal')

# 15) Ranking de Vendedores
st.header('🏆 Ranking de Vendedores')
r=df.groupby('Sales Team Member')['Total New ASV'].sum().reset_index().sort_values('Total New ASV', ascending=False)
r['Rank']=range(1,len(r)+1)
r['Total New ASV']=r['Total New ASV'].map('${:,.2f}'.format)
st.table(r[['Rank','Sales Team Member','Total New ASV']])

# 16) Gráficos adicionais
extras=[('Forecast Indicator','Pipeline por Forecast Indicator'),('Licensing Program Type','Pipeline por Licensing Program Type'),('Licensing Program','Pipeline por Licensing Program'),('Major OLPG1','Pipeline por Major OLPG1')]
for col,title in extras:
    if col in df.columns:
        st.header(f'📊 {title}')
        dcol=df.groupby(col)['Total New ASV'].sum().reset_index()
        figx=px.bar(dcol, x=col, y='Total New ASV', color=col, template='plotly_dark', text='Total New ASV')
        figx.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
        st.plotly_chart(figx, use_container_width=True)
        export_plot(figx,title.lower().replace(' ','_'))

# 17) Dados Brutos e ficha detalhada
st.header('📋 Dados Brutos')
disp=df.copy()
gb=GridOptionsBuilder.from_dataframe(disp)
gb.configure_default_column(cellStyle={'color':'white','backgroundColor':'#000000'})
numeric_cols=disp.select_dtypes(include=[np.number]).columns.tolist()
us_format=JsCode("function(params){return params.value!=null?params.value.toLocaleString('en-US',{minimumFractionDigits:2,maximum
