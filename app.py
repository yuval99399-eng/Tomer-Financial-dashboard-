import streamlit as st
import pandas as pd
import plotly.express as px

# הגדרת עמוד רחב
st.set_page_config(page_title="דשבורד פיננסי - טומר", layout="wide")

st.title("💰 ניתוח הוצאות וניהול תקציב")

# פונקציה להצגת חלון קופץ (Modal) עם פירוט העסקאות
@st.dialog("פירוט עסקאות")
def show_details_dialog(category, df_to_show):
    st.write(f"מציג את כל ההוצאות תחת הקטגוריה: **{category}**")
    # עיצוב הטבלה בתוך החלון הקופץ
    st.dataframe(
        df_to_show[['תאריך עסקה', 'שם בית עסק', 'סכום חיוב', 'סוג עסקה']], 
        use_container_width=True,
        hide_index=True
    )
    st.write(f"סה''כ לקטגוריה זו: **₪{df_to_show['סכום חיוב'].sum():,.2f}**")

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

uploaded_files = st.file_uploader("העלה קבצי בנק", type=["csv", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    all_dfs = []
    for file in uploaded_files:
        try:
            temp_df = load_and_clean_data(file)
            all_dfs.append(temp_df)
        except Exception as e:
            st.error(f"שגיאה בקובץ {file.name}: {e}")
    
    if all_dfs:
        full_df = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=['unique_id'])
        
        # --- סינונים ---
        available_months = sorted(full_df['Month-Year'].unique())
        st.sidebar.header("מסננים")
        selected_months = st.sidebar.multiselect("בחר חודשים", options=available_months, default=available_months[-1:])
        
        filtered_df = full_df[full_df['Month-Year'].isin(selected_months)]
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("חלוקה לקטגוריות (לחץ על פלח בעוגה)")
            # בחירת חודש לתצוגת העוגה
            pie_month = st.selectbox("בחר חודש לעוגה:", selected_months)
            pie_data = filtered_df[filtered_df['Month-Year'] == pie_month]
            
            if not pie_data.empty:
                summary = pie_data.groupby('ענף')['סכום חיוב'].sum().reset_index()
                fig_pie = px.pie(summary, values='סכום חיוב', names='ענף', hole=0.4)
                fig_pie.update_traces(textinfo='label+percent', textposition='inside')
                
                # תפיסת אירוע הלחיצה
                # הערה: לחיצה על המקרא (Legend) לא תפעיל את הדיאלוג, רק לחיצה על הפלח עצמו
                selection = st.plotly_chart(fig_pie, on_select="rerun", key="pie_chart")
                
                if selection and "selection" in selection and selection["selection"]["points"]:
                    # חילוץ שם הקטגוריה מהפלח שנלחץ
                    clicked_category = selection["selection"]["points"][0]["label"]
                    # סינון הנתונים עבור החלון הקופץ
                    details = pie_data[pie_data['ענף'] == clicked_category]
                    # הפעלת החלון הקופץ
                    show_details_dialog(clicked_category, details)

        with col2:
            st.subheader("השוואת הוצאות חודשית")
            monthly_comp = filtered_df.groupby(['Month-Year', 'ענף'])['סכום חיוב'].sum().reset_index()
            fig_bar = px.bar(monthly_comp, x='Month-Year', y='סכום חיוב', color='ענף', barmode='group')
            st.plotly_chart(fig_bar)

        # --- גרף מגמה כללי ---
        st.divider()
        st.subheader("מגמת הוצאות לאורך זמן")
        trend = full_df.groupby('Month-Year')['סכום חיוב'].sum().reset_index()
        st.line_chart(trend.set_index('Month-Year'))

else:
    st.info("אנא העלה קבצים כדי להתחיל.")
