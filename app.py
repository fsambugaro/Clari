import os
import logging
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import io
import json
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1) Configuração da página — deve vir antes de qualquer st.*
st.set_page_config(page_title="Dashboard Pipeline LATAM", layout="wide")

# 2) Definições de caminho
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(BASE_DIR, "Data")

# 2.1) Definição do arquivo de commits (precisa antes de qualquer uso)
SAVE_FILE = os.path.join(DIR, "committed_ids_by_member.json")

# 3) Configuração de logging
LOG_FILE = os.path.join(DIR, "debug_commits.log")
os.makedirs(DIR, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    filemode='a',
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.DEBUG
)

# 4) Verifica existência da pasta Data
if not os.path.isdir(DIR):
    st.error(f"🚨 Pasta de dados não encontrada: {DIR}")
    st.stop()

# 5) CSS para tema escuro e AgGrid
us_format = JsCode(
    "function(params){"
    "  return params.value!=null"
    "    ? params.value.toLocaleString('en-US',"
    "      {minimumFractionDigits:2,maximumFractionDigits:2})"
    "    : '';"
    "}"
)
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
    """,
    unsafe_allow_html=True
)


# 6) Título
st.title("📊 LATAM Pipeline Dashboard")

# 7) Carregamento dos CSVs na subpasta Data
@st.cache_data
def list_csv_files():
    return sorted([f for f in os.listdir(DIR) if f.lower().endswith('.csv')])

# 8) Carrega e sanitiza dados
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
    # Converte campos numéricos adicionais para float
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

# 9) Seleção de CSV
st.sidebar.header('📂 Select CSV file')
file = st.sidebar.selectbox('File:', [''] + list_csv_files())
if not file:
    st.info('Selecione um CSV para continuar')
    st.stop()

df = load_data(file)
full_df = df.copy()  # backup do dataset completo, antes dos filtros


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
st.sidebar.header('🔧 Filtros adicionais')

# --- 9.1) Fiscal Quarter
if 'Fiscal Quarter' in df.columns:
    sel_fq = st.sidebar.selectbox(
        'Fiscal Quarter',
        ['Todos'] + sorted(df['Fiscal Quarter'].dropna().unique())
    )
    if sel_fq != 'Todos':
        df = df[df['Fiscal Quarter'] == sel_fq]

# ←── 9.2) Forecast Indicator (cole exatamente este bloco) ──→
if 'Forecast Indicator' in df.columns:
    options_fc = sorted(df['Forecast Indicator'].dropna().unique())
    sel_fc = st.sidebar.multiselect(
        'Forecast Indicator',
        options_fc,
        default=options_fc
    )
    if sel_fc:
        df = df[df['Forecast Indicator'].isin(sel_fc)]
# ←─────────────────────────────────────────────────────────→

# --- 9.3) Deal Registration ID
if 'Deal Registration ID' in df.columns:
    sel_drid = st.sidebar.selectbox(
        'Deal Registration ID',
        ['Todos'] + sorted(df['Deal Registration ID'].dropna().unique()),
        key='filter_deal_registration_id'
    )

    if sel_drid != 'Todos':
        df = df[df['Deal Registration ID'] == sel_drid]

# --- 9.4) Dias desde Next Steps

if 'Days Since Next Steps Modified' in df.columns:
    labels = ['<=7 dias', '8-14 dias', '15-30 dias', '>30 dias']
    # 1) Garante float e preenche nulos com 0
    df['Days Since Next Steps Modified'] = pd.to_numeric(
        df['Days Since Next Steps Modified'], errors='coerce'
    ).fillna(0)
    # 2) Agrupa em bins, incluindo o menor valor
    df['DaysGroup'] = pd.cut(
        df['Days Since Next Steps Modified'],
        bins=[0,7,14,30,float('inf')],
        labels=labels,
        include_lowest=True
    )
    sel_dg = st.sidebar.selectbox(
        'Dias desde Next Steps',
        ['Todos'] + labels,
        key='filter_days_since_next_steps'
    )
    if sel_dg != 'Todos':
        df = df[df['DaysGroup'] == sel_dg]

# ... siga com os demais filtros abaixo ...



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
if 'sel_fc' in locals() and sel_fc:
    applied_filters.append(f"Forecast Indicator: {', '.join(sel_fc)}")
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



# 15) Seleção e exibição de Committed Deals por vendedor
st.markdown("---")
st.header("✅ Ajustar Committed Deals")

SAVE_FILE = os.path.join(DIR, "committed_ids_by_member.json")

# 1) Inicializa ou carrega estado
if "commit_ids_by_member" not in st.session_state:
    try:
        with open(SAVE_FILE, "r") as f:
            st.session_state.commit_ids_by_member = json.load(f)
    except FileNotFoundError:
        st.session_state.commit_ids_by_member = {}

current_member = sel_member if sel_member != "Todos" else "__ALL__"
prev_ids = st.session_state.commit_ids_by_member.get(current_member, [])

# 2) Upload / Download de IDs
st.subheader("📥 Upload / 📤 Download de lista de Commit IDs")
col1, col2 = st.columns(2)
with col1:
    uploaded = st.file_uploader("Upload CSV com Deal Registration ID", type="csv", key="upload_commits_15")
    if uploaded:
        df_u = pd.read_csv(uploaded, dtype=str)
        ids = df_u["Deal Registration ID"].dropna().astype(str).unique().tolist()
        st.session_state.commit_ids_by_member[current_member] = ids
        with open(SAVE_FILE, "w") as f:
            json.dump(st.session_state.commit_ids_by_member, f)
        st.success(f"Importados {len(ids)} IDs para {current_member}.")
        prev_ids = ids
with col2:
    if prev_ids:
        buf = io.StringIO()
        pd.DataFrame({"Deal Registration ID": prev_ids}).to_csv(buf, index=False)
        st.download_button("⬇️ Download lista atual",
                           data=buf.getvalue(),
                           file_name=f"commit_ids_{current_member}.csv",
                           mime="text/csv")

# 3) Prepara DataFrame com coluna de seleção
df = full_df.copy()
cols = ["Deal Registration ID", "Opportunity", "Total New ASV", "Stage", "Forecast Indicator"]
df = df[df["Forecast Indicator"].isin(["Upside", "Upside - Targeted"])][cols]
# Ajusta tipo
df["Deal Registration ID"] = df["Deal Registration ID"].astype(str)
# Marca os persistidos
df["selected"] = df["Deal Registration ID"].isin(prev_ids)

# 4) Exibe Experimental Data Editor para seleção múltipla
edited = st.experimental_data_editor(
    df,
    num_rows="dynamic",
    use_checkbox=True,
    hide_index=True,
    key=f"editor_commits_{current_member}"
)

# 5) Extrai seleção e persiste) Extrai seleção e persiste
sel_ids = edited.loc[edited["selected"], "Deal Registration ID"].tolist()
st.session_state.commit_ids_by_member[current_member] = sel_ids
with open(SAVE_FILE, "w") as f:
    json.dump(st.session_state.commit_ids_by_member, f)

# 6) Exibe resultado final
df_final = full_df[full_df["Deal Registration ID"].isin(sel_ids)].copy()
tot = df_final["Total New ASV"].sum()
st.markdown(f"---\n### 🚀 Upside deals to reach the commit — Total New ASV: {tot:,.2f}")
st.dataframe(df_final, use_container_width=True)

csv_out = df_final.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download Committed Deals (CSV)",
                   data=csv_out,
                   file_name=f"committed_deals_{current_member}.csv",
                   mime="text/csv")





#16 DEBUG (cole isto após o seu bloco #15)
#if os.path.exists(LOG_FILE):
#    with open(LOG_FILE, "r") as f:
#        lines = f.readlines()
#    # filtra apenas as linhas com nossas tags de debug
#    tags = [
#        "resp_rows raw",
#        "current_selected",
#        "visible_ids",
#        "prev_ids",
#        "hidden_prev",
#        "all_ids",
#        "commit_df IDs"
#    ]
#    filtered = [l for l in lines if any(tag in l for tag in tags)]
#    st.subheader("📝 Entradas relevantes do debug_commits.log")
#    if filtered:
#        st.code("".join(filtered[-20:]))
#    else:
#        st.info("Nenhuma entrada de debug encontrada ainda.")
#else:
#    st.info("Arquivo de log não existe: " + LOG_FILE)


# 16) Dados Brutos e ficha detalhada e ficha detalhada
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


