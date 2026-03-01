import streamlit as st
import pandas as pd
import plotly.express as px

# Page Settings
st.set_page_config(page_title="Tomer Financial Dashboard", layout="wide")
st.title("Financial Analysis 💰")

# --- DATA PROCESSING FUNCTIONS ---

def load_and_clean_data(file):
    """Processes credit card files"""
    if file.name.endswith('.xlsx'):
        df = pd.read_excel(file, skiprows=3)
    else:
        try:
            df = pd.read_csv(file, skiprows=3, encoding='windows-1255')
        except UnicodeDecodeError:
            file.seek(0)
            df = pd.read_csv(file, skiprows=3, encoding='utf-8')

    # Excel File New Classification 
    df.columns = [col.replace('\n', ' ').strip() for col in df.columns]
    df = df.dropna(subset=['תאריך עסקה', 'סכום חיוב'], how='all')
    df['תאריך עסקה'] = pd.to_datetime(df['תאריך עסקה'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['תאריך עסקה'])
    df['unique_id'] = df['תאריך עסקה'].astype(str) + df['שם בית עסק'] + df['סכום חיוב'].astype(str)
    df['Month-Year'] = df['תאריך עסקה'].dt.strftime('%Y-%m')
    df['סכום חיוב'] = pd.to_numeric(df['סכום חיוב'], errors='coerce').fillna(0)
    return df

def load_and_clean_bank_data(file):
    """Processes bank account activity files (Current Account)"""
    # Reading file with headers typically on row 6
    try:
        df = pd.read_csv(file, skiprows=5, encoding='windows-1255')
    except:
        file.seek(0)
        df = pd.read_csv(file, skiprows=5, encoding='utf-8')

    # Clean column names
    df.columns = [col.strip() for col in df.columns]
    
    # Remove empty rows
    df = df.dropna(subset=['תאריך'], how='all')
    
    # Handle Date conversion (Excel serial numbers vs strings)
    if pd.api.types.is_numeric_dtype(df['תאריך']):
        df['תאריך'] = pd.to_datetime(df['תאריך'], unit='D', origin='1899-12-30')
    else:
        df['תאריך'] = pd.to_datetime(df['תאריך'], dayfirst=True, errors='coerce')
    
    df = df.dropna(subset=['תאריך'])
    df['Month-Year'] = df['תאריך'].dt.strftime('%Y-%m')

    # Convert Credit (Income) and Debit (Expense) to numeric values
    for col in ['זכות', 'חובה']:
        if col in df.columns:
            # Cleaning string formatting like commas or spaces
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
        else:
            df[col] = 0.0
            
    return df

# --- INTERFACE TABS ---
# Separating Credit Analysis from Bank Activity for better UX
tab_credit, tab_bank = st.tabs(["💳 Credit Card Analysis", "🏦 Bank Account Activity"])

# --- TAB 1: CREDIT CARD ANALYSIS (EXISTING CODE) ---
with tab_credit:
    # Uploading File
    uploaded_files = st.file_uploader("Welcome 👋 Please Upload Your Files :)", type=["csv", "xlsx"], accept_multiple_files=True, key="credit_up")
    if uploaded_files:
        all_dfs = []
        for file in uploaded_files:
            try:
                temp_df = load_and_clean_data(file)
                all_dfs.append(temp_df)
            except Exception as e:
                st.error(f"Error in file {file.name}: {e}")
        
        if all_dfs:
            # No Duplication Allowed 
            full_df = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=['unique_id'])
            
            # Sidebars
            st.sidebar.header("⚙️ מסננים")
            available_months = sorted(full_df['Month-Year'].unique(), reverse=True)
            selected_months = st.sidebar.multiselect(
                "1.Month", 
                options=available_months, 
                default=available_months[:12] if len(available_months) > 1 else available_months
            )
            
            all_categories = sorted(full_df['ענף'].unique().tolist())
            selected_categories = st.sidebar.multiselect(
                "2.Category", 
                options=all_categories, 
                default=all_categories
            )
            filtered_df = full_df[
                (full_df['Month-Year'].isin(selected_months)) & 
                (full_df['ענף'].isin(selected_categories))
            ]
            
            # Graphs Design 
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("Pie Chart 📊")
                if len(selected_months) > 0:
                    pie_month = st.selectbox("For this month:", selected_months)
                    pie_data = filtered_df[filtered_df['Month-Year'] == pie_month]
                    if not pie_data.empty:
                        summary = pie_data.groupby('ענף')['סכום חיוב'].sum().reset_index()
                        fig_pie = px.pie(summary, values='סכום חיוב', names='ענף', hole=0.4)
                        fig_pie.update_traces(textinfo='label+percent', textposition='inside')
                        st.plotly_chart(fig_pie, use_container_width=True)
                    else:
                        st.warning("אין נתונים להצגה בחודש זה עם הסינונים הנוכחיים.")
                else:
                    st.info("אנא בחר לפחות חודש אחד בתפריט הצד.")

            with col2:
                st.subheader("Compare selected months 📈")
                if not filtered_df.empty:
                    monthly_comp = filtered_df.groupby(['Month-Year', 'ענף'])['סכום חיוב'].sum().reset_index()
                    fig_bar = px.bar(monthly_comp, x='ענף', y='סכום חיוב', color='Month-Year', barmode='group')
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("אין מספיק נתונים להשוואה.")

            # Row data table
            st.divider()
            if len(selected_months) > 0 and 'pie_data' in locals() and not pie_data.empty:
                st.subheader(f"📋 פירוט עסקאות לחודש {pie_month}")
                st.write(f"הטבלה מציגה את העסקאות עבור הקטגוריות שנבחרו במסנן בצד.")
                
                display_columns = ['תאריך עסקה', 'שם בית עסק', 'סכום חיוב', 'ענף', 'סוג עסקה', 'הערות']
                final_table = pie_data[display_columns].sort_values('תאריך עסקה', ascending=False)
                
                st.dataframe(final_table, use_container_width=True, hide_index=True)
                
                total_sum = final_table['סכום חיוב'].sum()
                st.info(f"סה''כ הוצאות מוצגות בטבלה: **₪{total_sum:,.2f}**")

# --- TAB 2: BANK ACCOUNT ACTIVITY (NEW SECTION) ---
with tab_bank:
    st.header("Bank Account Flow Analysis")
    uploaded_bank = st.file_uploader("Upload Bank Activity Files 👋", type=["csv", "xls", "xlsx"], accept_multiple_files=True, key="bank_up")
    
    if uploaded_bank:
        bank_dfs = []
        for b_file in uploaded_bank:
            try:
                bank_dfs.append(load_and_clean_bank_data(b_file))
            except Exception as e:
                st.error(f"Error in bank file {b_file.name}: {e}")
        
        if bank_dfs:
            combined_bank_df = pd.concat(bank_dfs, ignore_index=True)
            
            # Monthly Income vs Expenses calculation
            monthly_bank_summary = combined_bank_df.groupby('Month-Year').agg({'זכות': 'sum', 'חובה': 'sum'}).reset_index()
            monthly_bank_summary = monthly_bank_summary.sort_values('Month-Year')
            
            # Reshaping data for grouped bar chart
            bank_plot_data = monthly_bank_summary.melt(id_vars='Month-Year', value_vars=['זכות', 'חובה'], 
                                                       var_name='Transaction Type', value_name='Amount')
            
            st.subheader("Monthly Income (Zechut) vs Expenses (Chova)")
            # Using specific financial colors: Green for Income, Red for Expenses
            fig_bank_bar = px.bar(bank_plot_data, x='Month-Year', y='Amount', color='Transaction Type', 
                                 barmode='group', color_discrete_map={'זכות': '#2ECC71', 'חובה': '#E74C3C'})
            st.plotly_chart(fig_bank_bar, use_container_width=True)
            
            # Balance Summary Table
            st.divider()
            st.subheader("Monthly Balance Summary")
            monthly_bank_summary['Net Balance'] = monthly_bank_summary['זכות'] - monthly_bank_summary['חובה']
            
            # Formatting for display
            display_bank = monthly_bank_summary.copy()
            display_bank.columns = ['חודש', 'סה"כ הכנסות (זכות)', 'סה"כ הוצאות (חובה)', 'מאזן נטו']
            st.dataframe(display_bank.sort_values('חודש', ascending=False), use_container_width=True, hide_index=True)

else:
    if not uploaded_files:
        st.info("Welcome 👋 Please Upload Your Files :)")
