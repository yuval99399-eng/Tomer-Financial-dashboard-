import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="דשבורד פיננסי", layout="wide")

st.title("💰 ניתוח הוצאות רב-חודשי והשוואות")

def load_and_clean_data(file):
    # זיהוי סוג הקובץ
    if file.name.endswith('.xlsx'):
        df = pd.read_excel(file, skiprows=3)
    else:
        try:
            df = pd.read_csv(file, skiprows=3, encoding='windows-1255')
        except UnicodeDecodeError:
            file.seek(0)
            df = pd.read_csv(file, skiprows=3, encoding='utf-8')

    # ניקוי בסיסי
    df.columns = [col.replace('\n', ' ').strip() for col in df.columns]
    df = df.dropna(subset=['תאריך עסקה', 'סכום חיוב'], how='all')
    
    # המרת תאריך
    df['תאריך עסקה'] = pd.to_datetime(df['תאריך עסקה'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['תאריך עסקה'])
    
    # יצירת מפתח ייחודי למניעת כפילויות (תאריך + עסק + סכום)
    df['unique_id'] = df['תאריך עסקה'].astype(str) + df['שם בית עסק'] + df['סכום חיוב'].astype(str)
    
    # פורמט חודש לתצוגה
    df['Month-Year'] = df['תאריך עסקה'].dt.strftime('%Y-%m')
    df['סכום חיוב'] = pd.to_numeric(df['סכום חיוב'], errors='coerce').fillna(0)
    
    return df

uploaded_files = st.file_uploader("העלה קבצי בנק (ניתן לבחור כמה קבצים יחד)", type=["csv", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    all_dfs = []
    for file in uploaded_files:
        try:
            temp_df = load_and_clean_data(file)
            all_dfs.append(temp_df)
        except Exception as e:
            st.error(f"שגיאה בקובץ {file.name}: {e}")
    
    if all_dfs:
        # איחוד כל הקבצים והסרת כפילויות
        full_df = pd.concat(all_dfs, ignore_index=True)
        full_df = full_df.drop_duplicates(subset=['unique_id'])
        
        # --- תפריט צד (Sidebar) ---
        st.sidebar.header("הגדרות תצוגה")
        
        available_months = sorted(full_df['Month-Year'].unique())
        selected_months = st.sidebar.multiselect(
            "בחר חודשים להשוואה", 
            options=available_months, 
            default=available_months[-2:] if len(available_months) > 1 else available_months
        )
        
        all_categories = sorted(full_df['ענף'].unique().tolist())
        selected_categories = st.sidebar.multiselect(
            "סנן קטגוריות", 
            options=all_categories, 
            default=all_categories
        )
        
        filtered_df = full_df[
            (full_df['Month-Year'].isin(selected_months)) & 
            (full_df['ענף'].isin(selected_categories))
        ]
        
        # --- תצוגת השוואה ראשית ---
        col1, col2 = st.columns([1, 1])
        
        # משתנה לשמירת הבחירה מהגרף
        selected_category_from_pie = None

        with col1:
            st.subheader("מבנה הוצאות לפי חודש (עוגה)")
            pie_month = st.selectbox("הצג עוגה עבור חודש:", selected_months)
            pie_data = filtered_df[filtered_df['Month-Year'] == pie_month]
            
            if not pie_data.empty:
                # יצירת ה-DataFrame עבור העוגה
                category_summary = pie_data.groupby('ענף')['סכום חיוב'].sum().reset_index()
                fig_pie = px.pie(category_summary, values='סכום חיוב', names='ענף', hole=0.4)
                fig_pie.update_traces(textinfo='label+percent', textposition='inside')
                
                # שימוש ב-on_select כדי לתפוס את הלחיצה
                # הערה: זה דורש גרסת Streamlit 1.35.0 ומעלה
                event_data = st.plotly_chart(fig_pie, on_select="rerun")
                
                # חילוץ הקטגוריה שנלחצה
                if event_data and "selection" in event_data and "points" in event_data["selection"]:
                    points = event_data["selection"]["points"]
                    if len(points) > 0:
                        selected_category_from_pie = points[0]["label"]
            
        with col2:
            st.subheader("השוואת חודשים לפי קטגוריה")
            comparison_data = filtered_df.groupby(['Month-Year', 'ענף'])['סכום חיוב'].sum().reset_index()
            fig_comp = px.bar(comparison_data, x='ענף', y='סכום חיוב', color='Month-Year', barmode='group',
                             title="השוואת הוצאות בין חודשים נבחרים")
            st.plotly_chart(fig_comp)

        # --- פירוט עסקאות לפי לחיצה ---
        if selected_category_from_pie:
            st.divider()
            st.subheader(f"🔍 פירוט עסקאות עבור: {selected_category_from_pie} (חודש {pie_month})")
            
            # סינון הנתונים לפי הקטגוריה שנלחצה והחודש שמוצג בעוגה
            drill_down_df = pie_data[pie_data['ענף'] == selected_category_from_pie].sort_values('תאריך עסקה', ascending=False)
            
            # הצגת הנתונים בטבלה יפה
            st.dataframe(drill_down_df[['תאריך עסקה', 'שם בית עסק', 'סכום חיוב', 'סוג עסקה', 'הערות']], use_container_width=True)
            
            if st.button("נקה בחירה"):
                st.rerun()

        # --- גרף מגמה כללי ---
        st.divider()
        st.subheader("מגמת הוצאות לאורך זמן (כל החודשים שהועלו)")
        trend_data = full_df[full_df['ענף'].isin(selected_categories)].groupby('Month-Year')['סכום חיוב'].sum().reset_index()
        fig_trend = px.line(trend_data, x='Month-Year', y='סכום חיוב', markers=True, title="סה''כ הוצאות חודשיות")
        st.plotly_chart(fig_trend, use_container_width=True)

        # --- טבלת נתונים גולמיים ---
        with st.expander("צפה בכל העסקאות המסוננות (ללא קשר ללחיצה על הגרף)"):
            st.dataframe(filtered_df.sort_values('תאריך עסקה', ascending=False), use_container_width=True)

else:
    st.info("אנא העלה קובץ אחד או יותר (אקסל או CSV) כדי להתחיל בהשוואה.")
