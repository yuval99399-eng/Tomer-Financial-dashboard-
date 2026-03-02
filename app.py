import streamlit as st
import pandas as pd
import plotly.express as px
import io

# Page Settings
st.set_page_config(page_title="Tomer Financial Dashboard", layout="wide")
st.title("Financial Analysis 💰")

# SMART DATA PROCESSING FUNCTIONS 
def find_header_row(file, keywords): """Scans the first 20 rows of a file to find the row that contains most of the expected headers."""
    file.seek(0)
    if file.name.endswith(('.xls', '.xlsx')):
        df_peek = pd.read_excel(file, nrows=20, header=None)
    else:
        try:
            df_peek = pd.read_csv(file, nrows=20, header=None, encoding='windows-1255')
        except:
            file.seek(0)
            df_peek = pd.read_csv(file, nrows=20, header=None, encoding='utf-8')
    max_hits = 0
    header_idx = 0
    for i, row in df_peek.iterrows():
        row_str = " ".join(row.astype(str).values)
        hits = sum(1 for key in keywords if key in row_str)
        if hits > max_hits:
            max_hits = hits
            header_idx = i
    return header_idx

def smart_rename_columns(df): """ Refined logic to prevent duplicate column names. Priority is given to exact matches before trying to 'guess' via keywords."""
    df.columns = [str(col).replace('\n', ' ').strip() for col in df.columns]
    targets = {
        'תאריך עסקה': ['תאריך', 'עסקה'],
        'שם בית עסק': ['בית עסק', 'תיאור', 'פעולה'],
        'סכום חיוב': ['סכום', 'חיוב', 'בש"ח', 'בש""ח'],
        'ענף': ['ענף', 'קטגוריה']
    }
    
    new_mapping = {}
    used_targets = set()
    
    for target in targets:
        if target in df.columns:
            used_targets.add(target)
            
    for col in df.columns:
        if col in targets:
            continue
            
        for target, keywords in targets.items():
            if target in used_targets:
                continue  
            if target == 'תאריך עסקה' and any(k in col for k in keywords) and not any(k in col for k in ['סכום', 'חיוב']):
                new_mapping[col] = target
                used_targets.add(target)
                break
            elif target != 'תאריך עסקה' and any(k in col for k in keywords):
                new_mapping[col] = target
                used_targets.add(target)
                break        
    return df.rename(columns=new_mapping)


def load_and_clean_data(file): """Universal Credit Card Loader"""
    credit_keys = ['תאריך', 'עסקה', 'בית עסק', 'סכום']
    header_idx = find_header_row(file, credit_keys)
    file.seek(0)

    if file.name.endswith('.xlsx'):
        df = pd.read_excel(file, skiprows=header_idx)
    else:
        try:
            df = pd.read_csv(file, skiprows=header_idx, encoding='windows-1255')
        except:
            file.seek(0)
            df = pd.read_csv(file, skiprows=header_idx, encoding='utf-8')

    df = smart_rename_columns(df)
    df = df.loc[:, ~df.columns.duplicated()]

    if 'תאריך עסקה' not in df.columns or 'סכום חיוב' not in df.columns:
        return pd.DataFrame()

    df = df.dropna(subset=['תאריך עסקה', 'סכום חיוב'], how='all')
    df['תאריך עסקה'] = pd.to_datetime(df['תאריך עסקה'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['תאריך עסקה'])
    
    if 'ענף' not in df.columns:
        df['ענף'] = 'General / Uncategorized'
    df['ענף'] = df['ענף'].fillna('General / Uncategorized')
    df['unique_id'] = df['תאריך עסקה'].astype(str) + df.get('שם בית עסק', 'Unknown').astype(str) + df['סכום חיוב'].astype(str)
    df['Month-Year'] = df['תאריך עסקה'].dt.strftime('%Y-%m')
    df['סכום חיוב'] = pd.to_numeric(df['סכום חיוב'], errors='coerce').fillna(0)
    
    return df

def load_and_clean_bank_data(file): """Universal Bank Activity Loader"""
    bank_keys = ['זכות', 'חובה', 'פעולה', 'יתרה']
    header_idx = find_header_row(file, bank_keys)
    file.seek(0)
    
    if file.name.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file, skiprows=header_idx)
    else:
        try:
            df = pd.read_csv(file, skiprows=header_idx, encoding='windows-1255')
        except:
            file.seek(0)
            df = pd.read_csv(file, skiprows=header_idx, encoding='utf-8')

    df.columns = [str(col).strip() for col in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    
    date_col = next((c for c in df.columns if 'תאריך' in c), None)
    if not date_col:
        return pd.DataFrame()

    df = df.dropna(subset=[date_col], how='all')
    
    if pd.api.types.is_numeric_dtype(df[date_col]):
        df['תאריך_מסודר'] = pd.to_datetime(df[date_col], unit='D', origin='1899-12-30')
    else:
        df['תאריך_מסודר'] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
    
    df = df.dropna(subset=['תאריך_מסודר'])
    df['Month-Year'] = df['תאריך_מסודר'].dt.strftime('%Y-%m')

    for col in ['זכות', 'חובה']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
        else:
            df[col] = 0.0
            
    return df

# INTERFACE TABS 
tab_credit, tab_bank = st.tabs(["💳 Credit Card Analysis", "🏦 Bank Account Activity"])

#  TAB 1: CREDIT CARD ANALYSIS 
with tab_credit:
    uploaded_files = st.file_uploader("Upload Credit Files 👋", type=["csv", "xlsx"], accept_multiple_files=True, key="credit_up")
    
    if uploaded_files:
        all_dfs = []
        for file in uploaded_files:
            try:
                processed_df = load_and_clean_data(file)
                if not processed_df.empty:
                    all_dfs.append(processed_df)
            except Exception as e:
                st.error(f"Error processing {file.name}: {e}")
        
        if all_dfs:
            full_df = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=['unique_id'])
            
            st.sidebar.header("⚙️ Filters")
            available_months = sorted(full_df['Month-Year'].unique(), reverse=True)
            selected_months = st.sidebar.multiselect("1. Month", options=available_months, default=available_months[:12])
            all_categories = sorted(full_df['ענף'].unique().tolist())
            selected_categories = st.sidebar.multiselect("2. Category", options=all_categories, default=all_categories)
            filtered_df = full_df[(full_df['Month-Year'].isin(selected_months)) & (full_df['ענף'].isin(selected_categories))]
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Pie Chart 📊")
                if len(selected_months) > 0:
                    pie_month = st.selectbox("For this month:", selected_months, key="credit_month_sel")
                    pie_data = filtered_df[filtered_df['Month-Year'] == pie_month]
                    if not pie_data.empty:
                        summary = pie_data.groupby('ענף')['סכום חיוב'].sum().reset_index()
                        fig_pie = px.pie(summary, values='סכום חיוב', names='ענף', hole=0.4)
                        st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                st.subheader("Compare months 📈")
                if not filtered_df.empty:
                    m_comp = filtered_df.groupby(['Month-Year', 'ענף'])['סכום חיוב'].sum().reset_index()
                    fig_bar = px.bar(m_comp, x='ענף', y='סכום חיוב', color='Month-Year', barmode='group', text='סכום חיוב')
                    fig_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside', textangle=-90)
                    fig_bar.update_layout(yaxis_range=[0, m_comp['סכום חיוב'].max() * 1.25], margin=dict(t=50))
                    st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()
            if len(selected_months) > 0 and 'pie_data' in locals() and not pie_data.empty:
                st.subheader(f"📋 Transactions for {pie_month}")
                display_cols = ['תאריך עסקה', 'שם בית עסק', 'סכום חיוב', 'ענף', 'סוג עסקה']
                st.dataframe(pie_data[[c for c in display_cols if c in pie_data.columns]].sort_values('תאריך עסקה', ascending=False), use_container_width=True, hide_index=True)

# TAB 2: BANK ACCOUNT ACTIVITY 
with tab_bank:
    st.header("Bank Flow Analysis")
    uploaded_bank = st.file_uploader("Upload Bank Files 👋", type=["csv", "xlsx", "xls"], accept_multiple_files=True, key="bank_up")
    if uploaded_bank:
        bank_dfs = []
        for b_file in uploaded_bank:
            try:
                bank_dfs.append(load_and_clean_bank_data(b_file))
            except Exception as e:
                st.error(f"Error in bank file {b_file.name}: {e}")
        
        if bank_dfs:
            full_bank_df = pd.concat(bank_dfs, ignore_index=True)
            m_bank = full_bank_df.groupby('Month-Year').agg({'זכות': 'sum', 'חובה': 'sum'}).reset_index().sort_values('Month-Year')
            plot_data = m_bank.melt(id_vars='Month-Year', value_vars=['זכות', 'חובה'], var_name='Type', value_name='Amount')
            st.subheader("Monthly Income vs Expenses")
            fig_bank = px.bar(plot_data, x='Month-Year', y='Amount', color='Type', barmode='group', text='Amount',
                             color_discrete_map={'זכות': '#2ECC71', 'חובה': '#E74C3C'})
            fig_bank.update_traces(texttemplate='%{text:.3s}', textposition='outside', textangle=-90)
            fig_bank.update_layout(yaxis_range=[0, plot_data['Amount'].max() * 1.25], margin=dict(t=60))
            st.plotly_chart(fig_bank, use_container_width=True)

            # Detailed Bank Transactions Table 
            st.divider()
            available_bank_months = sorted(full_bank_df['Month-Year'].unique(), reverse=True)
            
            if available_bank_months:
                st.subheader("📋 Detailed Bank Transactions")
                bank_month_detail = st.selectbox("Select Month for Detail:", available_bank_months, key="bank_month_sel")
                month_detail_df = full_bank_df[full_bank_df['Month-Year'] == bank_month_detail].copy()
                cols_to_show = [c for c in month_detail_df.columns if c != 'תאריך_מסודר']
                st.dataframe(month_detail_df[cols_to_show].sort_values('Month-Year', ascending=False), 
                             use_container_width=True, hide_index=True)
                
                # Show summary row for that month
                total_income = month_detail_df['זכות'].sum()
                total_expense = month_detail_df['חובה'].sum()
                net_balance = total_income - total_expense
                
                # Display metrics for the selected month
                m_col1, m_col2, m_col3 = st.columns(3)
                m_col1.metric("Total Income (Zechut)", f"₪{total_income:,.2f}")
                m_col2.metric("Total Expenses (Chova)", f"₪{total_expense:,.2f}")
                m_col3.metric("Net Balance", f"₪{net_balance:,.2f}", delta=f"{net_balance:,.2f}")

if not uploaded_files and not uploaded_bank:
    st.info("Welcome 👋 Please Upload Your Files :)")
