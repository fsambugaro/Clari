import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from io import BytesIO

# 1) Initial settings
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
    .ag-theme-streamlit-dark .ag-header-cell { background-color: #111111 !important; }
    </style>
    """, unsafe_allow_html=True
)

# 2) Title
st.title("📊 LATAM Pipeline Dashboard")

# 3) CSV directory
DIR = os.getcwd()

# 4) List available CSVs
@st.cache_data
def list_csv_files():
    return sorted([f for f in os.listdir(DIR) if f.lower().endswith('.csv')])

# 5) Load & sanitize data
def load_data(path):
    df = pd.read_csv(os.path.join(DIR, path))
    df.columns = df.columns.str.strip()
    df['Opportunity'] = df.get('Opportunity', df.get('Opportunity ID', ''))
    df['Sales Team Member'] = df.get('Sales Team Member', df.get('Owner', '')).astype(str).str.strip()
    df['Stage'] = df['Stage'].astype(str).str.strip()
    df['Close Date'] = pd.to_datetime(df['Close Date'], errors='coerce')
    df['Total New ASV'] = (
        df['Total New ASV'].astype(str).str.replace(r"[\$,]", '', regex=True).astype(float)
    )
    for col in ['Renewal Bookings','Total DMe Est HASV','Total Attrition','Total TSV','Total Renewal ASV']:
        if col in df.columns:
            df[col] = (
                df[col].astype(str).str.replace(r"[\$,]", '', regex=True).astype(float)
            )
    if 'Sub Territory' in df.columns:
        df['Region'] = df['Sub Territory'].astype(str).apply(
            lambda x: 'Hispanic' if 'Hispanic' in x else ('Brazil' if 'Brazil' in x else 'Other')
        )
    else:
        df['Region'] = 'Other'
    return df

# 6) CSV selection
st.sidebar.header('📂 Select CSV')
file = st.sidebar.selectbox('File:', [''] + list_csv_files())
if not file:
    st.info('Select a CSV to continue')
    st.stop()
df = load_data(file)

# 7) Basic filters
st.sidebar.header('🔍 Filters')
members = ['All'] + sorted(df['Sales Team Member'].unique())
sel_member = st.sidebar.selectbox('Sales Team Member', members)
if sel_member != 'All': df = df[df['Sales Team Member'] == sel_member]
stages = sorted(df['Stage'].unique())
exclude = ['Closed - Clean Up', 'Closed - Lost']
default = [s for s in stages if s not in exclude]
sel_stages = st.sidebar.multiselect('Sales Stage', stages, default=default)
if sel_stages: df = df[df['Stage'].isin(sel_stages)]
regions = ['All', 'Brazil', 'Hispanic']
sel_region = st.sidebar.selectbox('Region', regions)
if sel_region != 'All': df = df[df['Sub Territory'].astype(str).str.contains(sel_region, case=False, na=False)]

# 8) Additional filters
st.sidebar.header('🔧 More Filters')
if 'Fiscal Quarter' in df.columns:
    fq_options = ['All'] + sorted(df['Fiscal Quarter'].dropna().unique())
    sel_fq = st.sidebar.selectbox('Fiscal Quarter', fq_options)
    if sel_fq != 'All': df = df[df['Fiscal Quarter'] == sel_fq]
if 'Forecast Indicator' in df.columns:
    fi_options = ['All'] + sorted(df['Forecast Indicator'].dropna().unique())
    sel_fi = st.sidebar.selectbox('Forecast Indicator', fi_options)
    if sel_fi != 'All': df = df[df['Forecast Indicator'] == sel_fi]
if 'Deal Registration ID' in df.columns:
    dr_options = ['All'] + sorted(df['Deal Registration ID'].dropna().unique())
    sel_dr = st.sidebar.selectbox('Deal Registration ID', dr_options)
    if sel_dr != 'All': df = df[df['Deal Registration ID'] == sel_dr]
if 'Days Since Next Steps Modified' in df.columns:
    df['Days Since Next Steps Modified'] = pd.to_numeric(df['Days Since Next Steps Modified'], errors='coerce')
    bins = [0,7,14,30,float('inf')]
    labels = ['<=7','8-14','15-30','>30']
    df['DaysGroup'] = pd.cut(df['Days Since Next Steps Modified'], bins=bins, labels=labels)
    sel_dg = st.sidebar.selectbox('Days Since Next Steps', ['All'] + labels)
    if sel_dg != 'All': df = df[df['DaysGroup'] == sel_dg]
if 'Licensing Program Type' in df.columns:
    lpt_options = ['All'] + sorted(df['Licensing Program Type'].dropna().unique())
    sel_lpt = st.sidebar.selectbox('Licensing Program Type', lpt_options)
    if sel_lpt != 'All': df = df[df['Licensing Program Type'] == sel_lpt]
if 'Opportunity' in df.columns:
    opp_options = ['All'] + sorted(df['Opportunity'].dropna().unique())
    sel_opp = st.sidebar.selectbox('Opportunity', opp_options)
    if sel_opp != 'All': df = df[df['Opportunity'] == sel_opp]
if 'Account Name' in df.columns:
    an_options = ['All'] + sorted(df['Account Name'].dropna().unique())
    sel_an = st.sidebar.selectbox('Account Name', an_options)
    if sel_an != 'All': df = df[df['Account Name'] == sel_an]
if 'Account Address: State/Province' in df.columns:
    st_options = ['All'] + sorted(df['Account Address: State/Province'].dropna().unique())
    sel_st = st.sidebar.selectbox('State/Province', st_options)
    if sel_st != 'All': df = df[df['Account Address: State/Province'] == sel_st]

# EDU filter
enum_df = df.copy()
edu_choice = st.sidebar.radio('EDU Filter', ['All','EDU','Others'], index=0)
if edu_choice == 'EDU': df = enum_df[enum_df['Sub Territory'].str.contains('EDU', case=False, na=False)]
elif edu_choice == 'Others': df = enum_df[~enum_df['Sub Territory'].str.contains('EDU', case=False, na=False)]
else: df = enum_df

# Totals summary
total_pipeline = df[df['Stage'].isin([
    '03 - Opportunity Qualification','04 - Circle of Influence',
    '05 - Solution Definition and Validation','06 - Customer Commit'])]['Total New ASV'].sum()
total_won = df[df['Stage'].isin(['07 - Execute to Close','Closed - Booked'])]['Total New ASV'].sum()
st.subheader(f"Total Pipeline: {total_pipeline:,.2f}   Total Won: {total_won:,.2f}")

# Mode bar config for downloads
chart_config = {'modeBarButtonsToAdd': ['downloadImage']}

# 9) Pipeline by Stage
st.header('🔍 Pipeline by Stage')
order = ['02 - Prospect','03 - Opportunity Qualification','04 - Circle of Influence',
         '05 - Solution Definition and Validation','06 - Customer Commit',
         '07 - Execute to Close','Closed - Booked']
phase = df[df['Stage'].isin(order)].groupby('Stage')['Total New ASV'].sum().reindex(order).reset_index()
fig1 = px.bar(phase, x='Total New ASV', y='Stage', orientation='h', template='plotly_dark', text='Total New ASV', color='Stage')
fig1.update_traces(texttemplate='%{text:,.2f}', textposition='inside')
st.plotly_chart(fig1, use_container_width=True, config=chart_config)

# 10) Pipeline Weekly
st.header('📈 Pipeline Weekly')
dfw = df.dropna(subset=['Close Date']).copy()
dfw['Week'] = dfw['Close Date'].dt.to_period('W').dt.to_timestamp()
weekly = dfw.groupby('Week')['Total New ASV'].sum().reset_index()
fig2 = px.line(weekly, x='Week', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig2.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig2, use_container_width=True, config=chart_config)

# 11) Pipeline Monthly
st.header('📆 Pipeline Monthly')
mon = dfw.copy()
mon['Month'] = mon['Close Date'].dt.to_period('M').dt.to_timestamp()
monthly = mon.groupby('Month')['Total New ASV'].sum().reset_index()
fig3 = px.line(monthly, x='Month', y='Total New ASV', markers=True, template='plotly_dark', text='Total New ASV')
fig3.update_traces(texttemplate='%{y:,.2f}', textposition='top center')
st.plotly_chart(fig3, use_container_width=True, config=chart_config)

# 12) Sales Ranking
st.header('🏆 Sales Ranking')
r = df.groupby('Sales Team Member')['Total New ASV'].sum().reset_index().sort_values('Total New ASV',ascending=False)
r['Rank'] = range(1, len(r)+1)
r['Total New ASV'] = r['Total New ASV'].map('${:,.2f}'.format)
st.table(r[['Rank','Sales Team Member','Total New ASV']])

# 13) Extra charts
extras = [('Forecast Indicator','Pipeline by Forecast Indicator'),
          ('Licensing Program Type','Pipeline by Licensing Program Type'),
          ('Licensing Program','Pipeline by Licensing Program'),
          ('Major OLPG1','Pipeline by Major OLPG1')]
for col,title in extras:
    if col in df.columns:
        st.header(f'📊 {title}')
        dcol = df.groupby(col)['Total New ASV'].sum().reset_index()
        figx = px.bar(dcol, x=col,y='Total New ASV',color=col,template='plotly_dark',text='Total New ASV')
        figx.update_traces(texttemplate='%{text:,.2f}',textposition='inside')
        st.plotly_chart(figx,use_container_width=True,config=chart_config)

# 14) Raw Data & records
st.header('📋 Raw Data')
disp = df.copy()
# download raw as CSV
csv_data = disp.to_csv(index=False).encode('utf-8')
st.download_button('Download data as CSV', data=csv_data, file_name='raw_data.csv', mime='text/csv')
# AgGrid
gb = GridOptionsBuilder.from_dataframe(disp)
bg_default = gb.configure_default_column(cellStyle={'color':'white','backgroundColor':'#000000'})
numeric_cols = disp.select_dtypes(include=[np.number]).columns.tolist()
format_js = JsCode("function(params){return params.value!=null?params.value.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}):''}")
for c in numeric_cols:
    gb.configure_column(c,type=['numericColumn','numberColumnFilter'],cellStyle={'textAlign':'right','color':'white','backgroundColor':'#000000'},cellRenderer=format_js)
gb.configure_selection(selection_mode='single',use_checkbox=True)
grid_resp = AgGrid(disp,gridOptions=gb.build(),theme='streamlit-dark',update_mode=GridUpdateMode.SELECTION_CHANGED,allow_unsafe_jscode=True,height=500)
sel = grid_resp['selected_rows']
sel_list = sel.to_dict('records') if isinstance(sel,pd.DataFrame) else sel or []
if sel_list:
    rec = sel_list[0]
    st.markdown('---')
    with st.expander(f"🗂 Record: {rec.get('Opportunity','')}",expanded=True):
        highlights = ['Stage','Total New ASV','Close Date','Total TSV','Original Close Date','Deal Registration ID','Owner','Total DMe Est HASV','Sales Team Member']
        cols = st.columns(3)
        for i,k in enumerate(highlights):
            with cols[i%3]: st.markdown(f"**{k}:** {rec.get(k,'')}")
        st.markdown('<hr/>',unsafe_allow_html=True)
        items = [(k,v) for k,v in rec.items() if k not in highlights+['Next Steps','Forecast Notes']]
        cols2 = st.columns(3)
        for i,(k,v) in enumerate(items):
            with cols2[i%3]: st.markdown(f"**{k}:** {v}")
        st.markdown('<hr/>',unsafe_allow_html=True)
        st.markdown("**Next Steps:**")
        st.write(rec.get('Next Steps',''))
        st.markdown('<hr/>',unsafe_allow_html=True)
        st.markdown("**Forecast Notes:**")
        st.write(rec.get('Forecast Notes',''))
