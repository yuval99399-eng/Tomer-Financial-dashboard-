import streamlit as st
import pandas as pd
import plotly.express as px

# Page Settings
st.set_page_config(page_title="Tomer Financial Dashboard", layout="wide")
st.title("Financial Analysis 💰")

def load_and_clean_data(file):
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
    
# Uploading File
uploaded_files = st.file_uploader("Welcome 👋 Please Upload You'r Files :)", type=["csv", "xlsx"], accept_multiple_files=True)
if uploaded_files:
    all_dfs = []
    for file in uploaded_files:
        try:
            temp_df = load_and_clean_data(file)
            all_dfs.append(temp_df)
        except Exception as e:
            st.error(f"שגיאה בקובץ {file.name}: {e}")
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
        
        # Graphs Disgn 
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
        if len(selected_months) > 0:
            st.subheader(f"📋 פירוט עסקאות לחודש {pie_month}")
            st.write(f"הטבלה מציגה את העסקאות עבור הקטגוריות שנבחרו במסנן בצד.")
            
            display_columns = ['תאריך עסקה', 'שם בית עסק', 'סכום חיוב', 'ענף', 'סוג עסקה', 'הערות']
            final_table = pie_data[display_columns].sort_values('תאריך עסקה', ascending=False)
            
            st.dataframe(final_table, use_container_width=True, hide_index=True)
            
            total_sum = final_table['סכום חיוב'].sum()
            st.info(f"סה''כ הוצאות מוצגות בטבלה: **₪{total_sum:,.2f}**")

else:
    st.info("Welcome 👋 Please Upload You'r Files :)")
