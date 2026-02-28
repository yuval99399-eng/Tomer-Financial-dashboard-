import streamlit as st
import pandas as pd
import plotly.express as px

# הגדרת עמוד רחב
st.set_page_config(page_title="דשבורד פיננסי - טומר", layout="wide")

st.title("💰 ניתוח הוצאות וניהול תקציב")

# 1. פונקציית החלון הקופץ (חייבת להיות מוגדרת לפני השימוש)
@st.dialog("פירוט עסקאות מעמיק", width="large")
def show_details_dialog(category, df_to_show, month):
    st.subheader(f"ענף: {category} | חודש: {month}")
    st.write(f"סה''כ הוצאות בקטגוריה: **₪{df_to_show['סכום חיוב'].sum():,.2f}**")
    
    # הצגת הטבלה
    st.dataframe(
        df_to_show[['תאריך עסקה', 'שם בית עסק', 'סכום חיוב', 'סוג עסקה', 'הערות']], 
        use_container_width=True,
        hide_index=True
    )
    
    if st.button("סגור"):
        st.rerun()

# 2. פונקציה לטעינת נתונים
def load_and_clean_data(file):
    if file.name.endswith('.xlsx'):
        df = pd.read_excel(file, skiprows=3)
    else:
        try:
            df = pd.read_csv(file, skiprows=3, encoding='windows-1255')
        except UnicodeDecodeError:
            file.seek(0)
            df = pd.read_csv(file, skiprows=3, encoding='utf-8')

    df.columns = [col.replace('\n', ' ').strip() for col in df.columns]
    df = df.dropna(subset=['תאריך עסקה', 'סכום חיוב'], how='all')
    df['תאריך עסקה'] = pd.to_datetime(df['תאריך עסקה'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['תאריך עסקה'])
    df['unique_id'] = df['תאריך עסקה'].astype(str) + df['שם בית עסק'] + df['סכום חיוב'].astype(str)
    df['Month-Year'] = df['תאריך עסקה'].dt.strftime('%Y-%m')
    df['סכום חיוב'] = pd.to_numeric(df['סכום חיוב'], errors='coerce').fillna(0)
    return df

uploaded_files = st.file_uploader("העלה קבצי בנק (CSV/XLSX)", type=["csv", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    all_dfs = []
    for file in uploaded_files:
        try:
            temp_df = load_and_clean_data(file)
            all_dfs.append(temp_df)
        except Exception as e:
            st.error(f"שגיאה בקובץ {file.name}: {e}")
    
    if all_dfs:
        # איחוד והסרת כפילויות
        full_df = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=['unique_id'])
        
        # --- תפריט צד (Sidebar) ---
        st.sidebar.header("מסננים")
        
        # פילטר חודשים
        available_months = sorted(full_df['Month-Year'].unique(), reverse=True)
        selected_months = st.sidebar.multiselect("בחר חודשים להצגה", options=available_months, default=available_months[:2])
        
        # פילטר קטגוריות (הוחזר!)
        all_categories = sorted(full_df['ענף'].unique().tolist())
        selected_categories = st.sidebar.multiselect("סנן קטגוריות ענף", options=all_categories, default=all_categories)
        
        # החלת סינון על הנתונים
        filtered_df = full_df[
            (full_df['Month-Year'].isin(selected_months)) & 
            (full_df['ענף'].isin(selected_categories))
        ]
        
        # --- תצוגה ראשית ---
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("מבנה הוצאות (לחץ על פלח בעוגה)")
            if len(selected_months) > 0:
                pie_month = st.selectbox("הצג עוגה עבור חודש:", selected_months)
                pie_data = filtered_df[filtered_df['Month-Year'] == pie_month]
                
                if not pie_data.empty:
                    summary = pie_data.groupby('ענף')['סכום חיוב'].sum().reset_index()
                    fig_pie = px.pie(summary, values='סכום חיוב', names='ענף', hole=0.4)
                    fig_pie.update_traces(textinfo='label+percent', textposition='inside')
                    
                    # שימוש ב-on_select כדי לתפוס לחיצות
                    selection = st.plotly_chart(fig_pie, on_select="rerun", key="main_pie")
                    
                    # בדיקה אם נלחץ פלח
                    if selection and "selection" in selection and selection["selection"]["points"]:
                        clicked_category = selection["selection"]["points"][0]["label"]
                        # שליפת נתונים ופתיחת החלון הקופץ
                        details_to_show = pie_data[pie_data['ענף'] == clicked_category]
                        show_details_dialog(clicked_category, details_to_show, pie_month)
                else:
                    st.warning("אין נתונים לחודש זה תחת הקטגוריות שנבחרו.")
            else:
                st.info("בחר חודש בתפריט הצד")

        with col2:
            st.subheader("השוואה בין חודשים נבחרים")
            if not filtered_df.empty:
                monthly_comp = filtered_df.groupby(['Month-Year', 'ענף'])['סכום חיוב'].sum().reset_index()
                fig_bar = px.bar(monthly_comp, x='ענף', y='סכום חיוב', color='Month-Year', barmode='group')
                st.plotly_chart(fig_bar)
            else:
                st.info("אין נתונים להשוואה")

        # --- מגמה ---
        st.divider()
        st.subheader("מגמת הוצאות חודשית (כללי)")
        trend_data = full_df.groupby('Month-Year')['סכום חיוב'].sum().reset_index().sort_values('Month-Year')
        fig_line = px.line(trend_data, x='Month-Year', y='סכום חיוב', markers=True)
        st.plotly_chart(fig_line, use_container_width=True)

else:
    st.info("אנא העלה קבצים כדי להתחיל.")
