import streamlit as st
# — Agora sim: configura página e injeta CSS —
st.set_page_config(page_title="Dashboard Pipeline LATAM") #, layout="wide"

import pandas as pd
import numpy as np
import plotly.express as px
import os
import io
import yaml
import streamlit_authenticator as stauth
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# — Carrega o YAML de credenciais —
with open('credentials.yaml') as f:
    config = yaml.safe_load(f)

# — Inicializa o autenticador —
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# — Exibe o formulário de login UMA vez, no main —
authenticator.login(location='main')

# — Lê o status de autenticação do session_state —
auth_status = st.session_state.get('authentication_status')
if auth_status is False:
    st.error('Usuário ou senha inválidos')
    st.stop()
elif auth_status is None:
    st.info('Por favor, faça login')
    st.stop()

# — Login OK: extrai name e username do session_state —
name     = st.session_state['name']
username = st.session_state['username']
st.sidebar.success(f"Bem-vindo, {name} 👋")


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
    """,
    unsafe_allow_html=True
)


# 2) Título
st.title("📊 LATAM Pipeline Dashboard")


# 3) Caminho dos CSVs — busca na subpasta "Data" ao lado do app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(BASE_DIR, "Data")

# Se a pasta não existir, interrompe com mensagem amigável
if not os.path.isdir(DIR):
    st.error(f"🚨 Data folder not found: {DIR}")
    st.stop()



# 4) Lista de CSVs disponíveis
@st.cache_data
def list_csv_files():
    return sorted([f for f in os.listdir(DIR) if f.lower().endswith('.csv')])

# 5) Carrega e sanitiza dados
def load_data(path):
    df = pd.read_csv(os.path.join(DIR, path))
    # 0) Extrai o tipo do CSV (sem extensão) e define o arquivo de commits


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

# Deriva o tipo do CSV e define um commit_file específico
csv_type    = os.path.splitext(file)[0]  

# … depois de df = load_data(file) …
csv_type = os.path.splitext(file)[0]



# … daí em diante vem todo o seu bloco 15 (seleção, merge e gravação) …


# limpa estado se trocou de CSV
if 'current_csv_type' not in st.session_state:
    st.session_state.current_csv_type = csv_type
else:
    if st.session_state.current_csv_type != csv_type:
        st.session_state.current_csv_type = csv_type
        st.session_state.upside_grid_counter = 0
        if 'committed_deals' in st.session_state:
            del st.session_state['committed_deals']


# 7) Filtros básicos
st.sidebar.header('🔍 Filters')
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
st.sidebar.header('🔧 Aditional Filters')

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
        'Days since Next Steps',
        ['Todos'] + labels,
        key='filter_days_since_next_steps'
    )
    if sel_dg != 'Todos':
        df = df[df['DaysGroup'] == sel_dg]


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
    st.markdown("**Applied filters:** " + " | ".join(applied_filters))
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
st.header('🔍 Pipeline Stage')
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
st.header('📈 Weekly Pipeline')
dfw = df.dropna(subset=['Close Date']).copy()
dfw['Week'] = dfw['Close Date'].dt.to_period('W').dt.to_timestamp()
weekly = dfw.groupby('Week')['Total New ASV'].sum().reset_index()
fig2 = px.line(weekly, x='Week', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig2.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig2, use_container_width=True, key='pipeline_weekly')
download_html(fig2, 'pipeline_weekly')

# 12) Pipeline Mensal
st.header('📆 Monthly Pipeline')
mon = dfw.copy()
mon['Month'] = mon['Close Date'].dt.to_period('M').dt.to_timestamp()
monthly = mon.groupby('Month')['Total New ASV'].sum().reset_index()
fig3 = px.line(monthly, x='Month', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig3.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig3, use_container_width=True, key='pipeline_monthly')
download_html(fig3, 'pipeline_monthly')

# 13) Ranking de Vendedores
st.header('🏆 Sales Team Ranking')
r = df.groupby('Sales Team Member')['Total New ASV'].sum().reset_index().sort_values('Total New ASV', ascending=False)
r['Rank'] = range(1, len(r) + 1)
r['Total New ASV'] = r['Total New ASV'].map('${:,.2f}'.format)
st.table(r[['Rank','Sales Team Member','Total New ASV']])

# 14) Gráficos adicionais
extras = [
    ('Forecast Indicator','Pipeline by Forecast Indicator'),
    ('Licensing Program Type','Pipeline by Licensing Program Type'),
    ('Licensing Program','Pipeline by Licensing Program'),
    ('Major OLPG1','Pipeline by Product')
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


# 15) Seleção e exibição de Committed Deals
st.markdown('---')
st.header(f'✅ Upside deals to reach commit — {csv_type}')

# 01 ── Início isolamento por usuário ──
user_dir   = os.path.join(BASE_DIR, "Data", username)
os.makedirs(user_dir, exist_ok=True)
commit_file = os.path.join(user_dir, f"committed_deals_{csv_type}.csv")

# 02 Inicializa commits salvos em sessão (ainda sem saber as colunas)
if 'committed_deals' not in st.session_state:
    if os.path.exists(commit_file):
        st.session_state.committed_deals = pd.read_csv(commit_file)
    else:
        # placeholder vazio — vamos ajustar as colunas depois
        st.session_state.committed_deals = pd.DataFrame()
# ── Fim isolamento por usuário ──



# 1) DataFrame base só com os Upside deals ainda abertos
commit_disp = df[
    df['Forecast Indicator'].fillna('').isin(['Upside', 'Upside - Targeted']) &
    (~df['Stage'].isin([
        'Closed - Booked',
        '07 - Execute to Close',
        '02 - Prospect'
    ]))
][[
    'Deal Registration ID',
    'Opportunity',
    'Sales Team Member',
    'Stage',
    'Close Date',
    'Total New ASV',
    'Next Steps'
]].copy()
commit_disp['Next Steps'] = commit_disp['Next Steps'].astype(str).str.slice(0,50)

# Se era DataFrame vazio, preencha agora com as colunas corretas
if st.session_state.committed_deals.empty:
    st.session_state.committed_deals = pd.DataFrame(columns=commit_disp.columns)


# 2) Inicializa commits salvos em sessão (com as colunas de commit_disp)
if 'committed_deals' not in st.session_state:
    if os.path.exists(commit_file):
        st.session_state.committed_deals = pd.read_csv(commit_file)
    else:
        st.session_state.committed_deals = pd.DataFrame(columns=commit_disp.columns)

# 3) Contador para resetar só o grid de Upside
if 'upside_grid_counter' not in st.session_state:
    st.session_state.upside_grid_counter = 0

# 4) Botão que limpa apenas a seleção de Upside Deals
if st.button("✔️ Limpar seleção de Upside Deals"):
    st.session_state.upside_grid_counter += 1

# 5) Exibe AgGrid para seleção de Upside Deals
gb = GridOptionsBuilder.from_dataframe(commit_disp)
gb.configure_default_column(cellStyle={'color':'white','backgroundColor':'#000000'})
gb.configure_column(
    'Total New ASV',
    type=['numericColumn','numberColumnFilter'],
    cellStyle={'textAlign':'right','color':'white','backgroundColor':'#000000'},
    cellRenderer=us_format
)
gb.configure_selection(selection_mode='multiple', use_checkbox=True)

grid_key = f"upside_deals_grid_{st.session_state.upside_grid_counter}"
resp = AgGrid(
    commit_disp,
    gridOptions=gb.build(),
    theme='streamlit-dark',
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    allow_unsafe_jscode=True,
    height=300,
    key=grid_key
)

# 6) Monta commit_df a partir da seleção
raw = resp.get('selected_rows')
if isinstance(raw, pd.DataFrame):
    sel = raw.to_dict('records')
elif isinstance(raw, list):
    sel = raw
else:
    sel = []
commit_df = pd.DataFrame(sel, columns=commit_disp.columns)

# 7) Edição e merge incremental
if not commit_df.empty:
    st.markdown('---')
    st.subheader('✏️ Edite os Committed Deals antes de confirmar')

    # Editor nativo para ajustar ou remover linhas
    edited_df = st.data_editor(
        commit_df,
        num_rows="dynamic",
        use_container_width=True
    )

    # 7.1) Merge sem perder itens antigos
    existing = st.session_state.committed_deals
    combined = pd.concat([existing, edited_df], ignore_index=True)
    combined = combined.drop_duplicates(
        subset=['Deal Registration ID'],
        keep='first'
    )
    st.session_state.committed_deals = combined

    # 7.2) Persiste no CSV correto
    combined.to_csv(commit_file, index=False)

# 8) Editor in-place dos Committed Deals já persistidos
st.markdown('---')
st.subheader('✏️ Edit Committed Deals')

edited_commits = st.data_editor(
    st.session_state.committed_deals,
    num_rows="dynamic",
    use_container_width=True
)

# Se houve alteração, atualiza e regrava
if not edited_commits.equals(st.session_state.committed_deals):
    st.session_state.committed_deals = edited_commits.copy()
    st.session_state.committed_deals.to_csv(commit_file, index=False)

# 9) Recalcula o Total New ASV após edição/exclusão
total_commits = st.session_state.committed_deals['Total New ASV'].sum()
st.header(f"Committed Deals — Total New ASV: {total_commits:,.2f}")

# 10) Botão de download da versão editada
csv_commits = st.session_state.committed_deals.to_csv(index=False).encode('utf-8')
st.download_button(
    '⬇️ Download Committed Deals (CSV)',
    data=csv_commits,
    file_name=f'committed_deals_{csv_type}.csv',
    mime='text/csv',
    key='download_committed_deals'
)


# 16) Dados Brutos e ficha detalhada e ficha detalhada
st.header('📋 Raw Data')
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


