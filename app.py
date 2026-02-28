import streamlit as st
import pandas as pd
import plotly.express as px

# הגדרת עמוד רחב
st.set_page_config(page_title="דשבורד פיננסי - טומר", layout="wide")

st.title("💰 ניתוח הוצאות וניהול תקציב")

def load_and_clean_data(file):
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
    
    # יצירת מפתח ייחודי למניעת כפילויות
    df['unique_id'] = df['תאריך עסקה'].astype(str) + df['שם בית עסק'] + df['סכום חיוב'].astype(str)
    
    # פורמט חודש לתצוגה
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
        st.sidebar.header("⚙️ מסננים")
        
        available_months = sorted(full_df['Month-Year'].unique(), reverse=True)
        selected_months = st.sidebar.multiselect(
            "1. בחר חודשים להשוואה", 
            options=available_months, 
            default=available_months[:2] if len(available_months) > 1 else available_months
        )
        
        all_categories = sorted(full_df['ענף'].unique().tolist())
        selected_categories = st.sidebar.multiselect(
            "2. סנן קטגוריות ענף", 
            options=all_categories, 
            default=all_categories
        )
        
        # סינון ה-DataFrame המרכזי לפי חודשים וקטגוריות שנבחרו בצד
        filtered_df = full_df[
            (full_df['Month-Year'].isin(selected_months)) & 
            (full_df['ענף'].isin(selected_categories))
        ]
        
        # --- תצוגה גרפית ---
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📊 מבנה הוצאות")
            if len(selected_months) > 0:
                # בחירת חודש ספציפי לעוגה מתוך אלו שנבחרו בסינון
                pie_month = st.selectbox("הצג עוגה עבור חודש:", selected_months)
                
                # הנתונים לעוגה - רק החודש הנבחר והקטגוריות המסוננות
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
            st.subheader("📈 השוואת חודשים נבחרים")
            if not filtered_df.empty:
                monthly_comp = filtered_df.groupby(['Month-Year', 'ענף'])['סכום חיוב'].sum().reset_index()
                fig_bar = px.bar(monthly_comp, x='ענף', y='סכום חיוב', color='Month-Year', barmode='group')
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("אין מספיק נתונים להשוואה.")

        # --- הפיצר החדש: טבלת פירוט דינמית בתחתית ---
        st.divider()
        if len(selected_months) > 0:
            st.subheader(f"📋 פירוט עסקאות לחודש {pie_month}")
            st.write(f"הטבלה מציגה את העסקאות עבור הקטגוריות שנבחרו במסנן בצד.")
            
            # הטבלה תמיד תראה מה שקורה בתוך ה-pie_data (שכבר מסונן לפי חודש וקטגוריות)
            display_columns = ['תאריך עסקה', 'שם בית עסק', 'סכום חיוב', 'ענף', 'סוג עסקה', 'הערות']
            
            # מיון לפי תאריך (מהחדש לישן)
            final_table = pie_data[display_columns].sort_values('תאריך עסקה', ascending=False)
            
            # הצגת הטבלה
            st.dataframe(final_table, use_container_width=True, hide_index=True)
            
            # הצגת סיכום כספי מתחת לטבלה
            total_sum = final_table['סכום חיוב'].sum()
            st.info(f"סה''כ הוצאות מוצגות בטבלה: **₪{total_sum:,.2f}**")
        
        # --- מגמה כללית ---
        st.divider()
        st.subheader("📉 מגמת הוצאות לאורך כל התקופה")
        trend_data = full_df.groupby('Month-Year')['סכום חיוב'].sum().reset_index().sort_values('Month-Year')
        fig_line = px.line(trend_data, x='Month-Year', y='סכום חיוב', markers=True)
        st.plotly_chart(fig_line, use_container_width=True)

else:
    st.info("👋 ברוך הבא! אנא העלה את קבצי הבנק שלך (CSV או אקסל) כדי להתחיל בניתוח.")
