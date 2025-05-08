import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1) Initial configuration
st.set_page_config(page_title="LATAM Pipeline Dashboard", layout="wide")
# Dark theme CSS
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
    /* AgGrid dark theme */
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

# 2) Title
st.title("📊 LATAM Pipeline Dashboard")

# 3) Working directory
DIR = os.getcwd()

# 4) Available CSVs
@st.cache_data
def list_csv_files():
    return sorted([f for f in os.listdir(DIR) if f.lower().endswith('.csv')])

# 5) Load and sanitize data
def load_data(path):
    df = pd.read_csv(os.path.join(DIR, path))
    df.columns = df.columns.str.strip()
    df['Opportunity'] = df.get('Opportunity', df.get('Opportunity ID', ''))
    df['Sales Team Member'] = df.get('Sales Team Member', df.get('Owner', '')).astype(str).str.strip()
    df['Stage'] = df['Stage'].astype(str).str.strip()
    df['Close Date'] = pd.to_datetime(df['Close Date'], errors='coerce')
    # Numeric fields
    for col in ['Total New ASV','Renewal Bookings','Total DMe Est HASV','Total Attrition','Total TSV','Total Renewal ASV']:
        if col in df.columns:
            df[col] = (
                df[col].astype(str).str.replace(r"[\$,]", '', regex=True).astype(float)
            )
    # Region
    if 'Sub Territory' in df.columns:
        df['Region'] = df['Sub Territory'].astype(str).apply(
            lambda x: 'Hispanic' if 'Hispanic' in x else ('Brazil' if 'Brazil' in x else 'Other')
        )
    else:
        df['Region'] = 'Other'
    return df

# 6) CSV selection
st.sidebar.header('📂 Select CSV')
file = st.sidebar.selectbox('Choose file:', [''] + list_csv_files())
if not file:
    st.info('Please select a CSV to continue')
    st.stop()

# Load data
df = load_data(file)

# 7) Basic filters
st.sidebar.header('🔍 Filters')
# Sales Team Member
members = ['All'] + sorted(df['Sales Team Member'].unique())
sel_member = st.sidebar.selectbox('Sales Team Member', members)
if sel_member != 'All': df = df[df['Sales Team Member'] == sel_member]
# Sales Stage
stages = sorted(df['Stage'].unique())
excluded = ['Closed - Clean Up', 'Closed - Lost']
default = [s for s in stages if s not in excluded]
sel_stages = st.sidebar.multiselect('Sales Stage', stages, default)
if sel_stages: df = df[df['Stage'].isin(sel_stages)]
# Region
regions = ['All', 'Brazil', 'Hispanic']
sel_region = st.sidebar.selectbox('Region', regions)
if sel_region != 'All': df = df[df['Region'] == sel_region]

# 8) Additional filters
st.sidebar.header('🔧 Additional Filters')
if 'Fiscal Quarter' in df.columns:
    sel_fq = st.sidebar.selectbox('Fiscal Quarter', ['All'] + sorted(df['Fiscal Quarter'].dropna().unique()))
    if sel_fq != 'All': df = df[df['Fiscal Quarter'] == sel_fq]
if 'Forecast Indicator' in df.columns:
    sel_fc = st.sidebar.selectbox('Forecast Indicator', ['All'] + sorted(df['Forecast Indicator'].dropna().unique()))
    if sel_fc != 'All': df = df[df['Forecast Indicator'] == sel_fc]
if 'Deal Registration ID' in df.columns:
    sel_drid = st.sidebar.selectbox('Deal Registration ID', ['All'] + sorted(df['Deal Registration ID'].dropna().unique()))
    if sel_drid != 'All': df = df[df['Deal Registration ID'] == sel_drid]
if 'Days Since Next Steps Modified' in df.columns:
    df['Days Since Next Steps Modified'] = pd.to_numeric(df['Days Since Next Steps Modified'], errors='coerce')
    bins = [0, 7, 14, 30, np.inf]
    labels = ['<=7 days', '8-14 days', '15-30 days', '>30 days']
    df['DaysGroup'] = pd.cut(df['Days Since Next Steps Modified'], bins=bins, labels=labels)
    sel_dg = st.sidebar.selectbox('Days Since Next Steps', ['All'] + labels)
    if sel_dg != 'All': df = df[df['DaysGroup'] == sel_dg]
if 'Licensing Program Type' in df.columns:
    sel_lpt = st.sidebar.selectbox('Licensing Program Type', ['All'] + sorted(df['Licensing Program Type'].dropna().unique()))
    if sel_lpt != 'All': df = df[df['Licensing Program Type'] == sel_lpt]
if 'Opportunity' in df.columns:
    sel_op = st.sidebar.selectbox('Opportunity', ['All'] + sorted(df['Opportunity'].dropna().unique()))
    if sel_op != 'All': df = df[df['Opportunity'] == sel_op]
if 'Account Name' in df.columns:
    sel_an = st.sidebar.selectbox('Account Name', ['All'] + sorted(df['Account Name'].dropna().unique()))
    if sel_an != 'All': df = df[df['Account Name'] == sel_an]

# 9) Totals
total_pipeline = df[df['Stage'].isin([
    '02 - Prospect', '03 - Opportunity Qualification', '04 - Circle of Influence',
    '05 - Solution Definition and Validation', '06 - Customer Commit'
])]['Total New ASV'].sum()
total_won = df[df['Stage'].isin(['07 - Execute to Close', 'Closed - Booked'])]['Total New ASV'].sum()
st.subheader(f"Total Pipeline: {total_pipeline:,.2f}   Total Won: {total_won:,.2f}")

# 10) Pipeline by Stage
st.header('🔍 Pipeline by Stage')
order = [
    '02 - Prospect', '03 - Opportunity Qualification', '04 - Circle of Influence',
    '05 - Solution Definition and Validation', '06 - Customer Commit',
    '07 - Execute to Close', 'Closed - Booked'
]
phase = df[df['Stage'].isin(order)].groupby('Stage')['Total New ASV'].sum().reindex(order).reset_index()
fig = px.bar(
    phase, x='Total New ASV', y='Stage', orientation='h', template='plotly_dark',
    text='Total New ASV', color='Stage', color_discrete_sequence=px.colors.qualitative.Vivid
)
fig.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
st.plotly_chart(fig, use_container_width=True)
# Download as HTML
html = fig.to_html(include_plotlyjs='cdn')
st.download_button('Download Chart (HTML)', html, file_name='pipeline_by_stage.html', mime='text/html')

# 11) Weekly Pipeline
st.header('📈 Weekly Pipeline')
dfw = df.dropna(subset=['Close Date']).copy()
dfw['Week'] = dfw['Close Date'].dt.to_period('W').dt.to_timestamp()
weekly = dfw.groupby('Week')['Total New ASV'].sum().reset_index()
fig = px.line(weekly, x='Week', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig, use_container_width=True)
html = fig.to_html(include_plotlyjs='cdn')
st.download_button('Download Chart (HTML)', html, file_name='weekly_pipeline.html', mime='text/html')

# 12) Monthly Pipeline
st.header('📆 Monthly Pipeline')
mon = dfw.copy()
mon['Month'] = mon['Close Date'].dt.to_period('M').dt.to_timestamp()
monthly = mon.groupby('Month')['Total New ASV'].sum().reset_index()
fig = px.line(monthly, x='Month', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig, use_container_width=True)
html = fig.to_html(include_plotlyjs='cdn')
st.download_button('Download Chart (HTML)', html, file_name='monthly_pipeline.html', mime='text/html')

# 13) Sales Rep Ranking
st.header('🏆 Sales Rep Ranking')
r = df.groupby('Sales Team Member')['Total New ASV'].sum().reset_index().sort_values('Total New ASV', ascending=False)
r['Rank'] = range(1, len(r) + 1)
r['Total New ASV'] = r['Total New ASV'].map('${:,.2f}'.format)
st.table(r[['Rank', 'Sales Team Member', 'Total New ASV']])

# 14) Additional charts
extras = [
    ('Forecast Indicator', 'Pipeline by Forecast Indicator'),
    ('Licensing Program Type', 'Pipeline by Licensing Program Type'),
    ('Licensing Program', 'Pipeline by Licensing Program'),
    ('Major OLPG1', 'Pipeline by Major OLPG1')
]
for col, title in extras:
    if col in df.columns:
        st.header(f'📊 {title}')
        dcol = df.groupby(col)['Total New ASV'].sum().reset_index()
        fig = px.bar(dcol, x=col, y='Total New ASV', text='Total New ASV', template='plotly_dark', color=col, color_discrete_sequence=px.colors.qualitative.Vivid)
        fig.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
        st.plotly_chart(fig, use_container_width=True)
        html = fig.to_html(include_plotlyjs='cdn')
        fname = title.replace(' ', '_').lower() + '.html'
        st.download_button('Download Chart (HTML)', html, file_name=fname, mime='text/html')

# 15) Raw Data and detail
st.header('📋 Raw Data')
# Download filtered data
st.download_button('Download Data', df.to_csv(index=False), file_name='filtered_data.csv', mime='text/csv')
# Display
disp = df.copy()
gb = GridOptionsBuilder.from_dataframe(disp)
gb.configure_default_column(cellStyle={'color':'white','backgroundColor':'#000000'})
numeric_cols = disp.select_dtypes(include=[np.number]).columns.tolist()
us_format = JsCode("function(params){return params.value!=null?params.value.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}):''}")
for c in numeric_cols:
    gb.configure_column(
        c,
        type=['numericColumn','numberColumnFilter'],
        cellStyle={'textAlign':'right','color':'white','backgroundColor':'#000000'},
        cellRenderer=us_format
    )
gb.configure_selection(selection_mode='single', use_checkbox=True)
grid_resp = AgGrid(
    disp,
    gridOptions=gb.build(),
    theme='streamlit-dark',
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    allow_unsafe_jscode=True,
    height=500
)
sel = grid_resp['selected_rows'] or []
if sel:
    rec = sel[0]
    st.markdown('---')
    with st.expander(f"🗂 Record: {rec.get('Opportunity','')}", expanded=True):
        # ... keep original detail logic ...
        pass
