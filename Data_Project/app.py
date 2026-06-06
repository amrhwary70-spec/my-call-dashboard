import streamlit as st
import pandas as pd
import glob
import io
from datetime import datetime

# ========== إعدادات الصفحة ==========
st.set_page_config(
    page_title="AI Call Center Dashboard",
    page_icon="📊",
    layout="wide"
)

# ========== Title ==========
st.title("🔥 AI SMART CALL CENTER DASHBOARD")
st.markdown("---")

# ========== Sidebar: اختيار الملف ==========
st.sidebar.header("📁 Select Data File")

files = glob.glob("*.csv")
if not files:
    st.error("❌ No CSV files found in current directory!")
    st.stop()

selected_file = st.sidebar.selectbox("Choose CSV File", files)

# ========== تحميل البيانات ==========
@st.cache_data(ttl=60)
def load_data(file):
    try:
        df = pd.read_csv(file, sep=None, engine="python", encoding="utf-8")
        return df
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return pd.DataFrame()

df = load_data(selected_file)

if df.empty:
    st.warning("⚠️ No data loaded. Please check your file.")
    st.stop()

# ========== تنظيف ومعالجة البيانات ==========
def clean_data(df):
    df = df.copy()
    
    # تنظيف status
    df['status'] = df['status'].astype(str).str.strip().str.upper()
    
    # عمود Answered
    df['Answered'] = df['status'].apply(
        lambda x: 0 if x in ['NA', 'NO ANSWER', 'DROP', 'DROP?', 'EMPTY'] else 1
    )
    
    # عمود Sale
    df['Sale'] = df['status'].apply(
        lambda x: 1 if x == 'SALE' else 0
    )
    
    # معالجة التاريخ والوقت
    if 'call_date' in df.columns:
        df['call_date'] = pd.to_datetime(df['call_date'], errors='coerce')
        df['hour'] = df['call_date'].dt.hour
    else:
        df['hour'] = 12
    
    # تنظيف الأعمدة الرقمية
    if 'length_in_sec' in df.columns:
        df['length_in_sec'] = pd.to_numeric(df['length_in_sec'], errors='coerce').fillna(0)
    
    # AI Score
    df['AI_Score'] = (
        df['Answered'] * 2 +
        (df['length_in_sec'] > 60).astype(int) +
        df['Sale'] * 5
    )
    
    def classify(score):
        if score >= 6:
            return "🔥 Hot Lead"
        elif score >= 3:
            return "⚡ Warm Lead"
        else:
            return "❄️ Cold Lead"
    
    df['AI_Lead'] = df['AI_Score'].apply(classify)
    
    return df

df = clean_data(df)

# ========== Sidebar Filters ==========
st.sidebar.header("📊 Filters")

# فلتر الـ Agents
if 'user' in df.columns:
    all_agents = df['user'].dropna().unique().tolist()
    selected_agents = st.sidebar.multiselect(
        "Select Agents",
        options=all_agents,
        default=all_agents
    )
    if selected_agents:
        df = df[df['user'].isin(selected_agents)]

# فلتر الـ States
if 'state' in df.columns:
    all_states = df['state'].dropna().unique().tolist()
    selected_states = st.sidebar.multiselect(
        "Select States",
        options=all_states,
        default=all_states
    )
    if selected_states:
        df = df[df['state'].isin(selected_states)]

# فلتر آخر ساعات (Time Filter)
st.sidebar.subheader("⏰ Time Filter")
hours_back = st.sidebar.slider("Show last N hours", min_value=1, max_value=168, value=24)

if 'call_date' in df.columns and len(df) > 0:
    latest_date = df['call_date'].max()
    if pd.notna(latest_date):
        cutoff_time = latest_date - pd.Timedelta(hours=hours_back)
        df = df[df['call_date'] >= cutoff_time]
        st.sidebar.info(f"📅 Showing last {hours_back} hours")

# زر تحديث الملفات
if st.sidebar.button("🔄 Refresh File List"):
    st.cache_data.clear()
    st.rerun()

# ========== حساب الـ KPIs ==========
total_calls = len(df)
answered = df['Answered'].sum()
sales = df['Sale'].sum()

contact_rate = (answered / total_calls) * 100 if total_calls > 0 else 0
conversion_rate = (sales / answered) * 100 if answered > 0 else 0

# ========== KPI Cards ==========
st.subheader("📈 Key Performance Indicators")
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Calls", f"{total_calls:,}")
col2.metric("Answered Calls", f"{answered:,}")
col3.metric("Sales", f"{sales:,}")
col4.metric("Contact Rate", f"{contact_rate:.1f}%")
col5.metric("Conversion Rate", f"{conversion_rate:.1f}%")

st.markdown("---")

# ========== List Quality Assessment ==========
st.subheader("📋 List Quality Assessment")

if total_calls > 0:
    list_answered_rate = (answered / total_calls) * 100
    list_sales_rate = (sales / total_calls) * 100
    dnc_count = df['status'].isin(['DNC', 'DO NOT CALL']).sum()
    list_dnc_rate = (dnc_count / total_calls) * 100

    quality_score = (
        (list_answered_rate * 0.4) +
        (list_sales_rate * 0.5) +
        max(0, (100 - list_dnc_rate) * 0.1)
    )

    if quality_score >= 70:
        quality_rating = "🟢 Excellent List! 🔥"
        quality_color = "green"
    elif quality_score >= 50:
        quality_rating = "🟡 Good List 👍"
        quality_color = "orange"
    elif quality_score >= 30:
        quality_rating = "🟠 Average List 📊"
        quality_color = "gold"
    else:
        quality_rating = "🔴 Poor List ⚠️"
        quality_color = "red"

    col_q1, col_q2, col_q3, col_q4 = st.columns(4)

    with col_q1:
        st.metric("Answer Rate", f"{list_answered_rate:.1f}%")
    with col_q2:
        st.metric("Sales Rate", f"{list_sales_rate:.1f}%")
    with col_q3:
        st.metric("DNC Rate", f"{list_dnc_rate:.1f}%")
    with col_q4:
        st.markdown(f"### {quality_rating}")
        st.caption(f"Quality Score: {quality_score:.1f}/100")

    st.markdown("**💡 Improvement Tips:**")
    tips = []
    if list_answered_rate < 30:
        tips.append("⏰ Try calling at different hours (check 'Answered by Hour' chart)")
    if list_sales_rate < 5:
        tips.append("🎯 Review agent script or targeting criteria")
    if list_dnc_rate > 20:
        tips.append("🚫 Too many DNCs - consider list scrubbing")

    if tips:
        for tip in tips:
            st.warning(tip)
    else:
        st.success("✅ List looks great! No major issues detected.")
else:
    st.info("No data to assess list quality.")

st.markdown("---")

# ========== Charts Section ==========
st.subheader("📊 Performance Charts")

col_ch1, col_ch2 = st.columns(2)

with col_ch1:
    st.markdown("**📈 Sales by Hour**")
    if not df.empty and 'hour' in df.columns:
        sales_by_hour = df.groupby('hour')['Sale'].sum()
        st.bar_chart(sales_by_hour)
    else:
        st.info("No hour data available")

with col_ch2:
    st.markdown("**📞 Answered Calls by Hour**")
    if not df.empty and 'hour' in df.columns:
        answered_by_hour = df.groupby('hour')['Answered'].sum()
        st.line_chart(answered_by_hour)
    else:
        st.info("No hour data available")

st.markdown("---")

# ========== AI Section ==========
st.subheader("🤖 AI Lead Analysis")

col_ai1, col_ai2 = st.columns(2)

with col_ai1:
    st.markdown("**Lead Distribution**")
    lead_counts = df['AI_Lead'].value_counts()
    st.bar_chart(lead_counts)

with col_ai2:
    st.markdown("**🔥 Top Smart Leads**")
    if 'phone_number_dialed' in df.columns:
        top_leads = df.sort_values(by='AI_Score', ascending=False)[
            ['phone_number_dialed', 'state', 'AI_Score', 'AI_Lead']
        ].head(10)
        st.dataframe(top_leads, use_container_width=True)
    else:
        st.info("No phone number data available")

st.markdown("---")

# ========== Agent Performance ==========
st.subheader("👨‍💼 Agent Performance")

if 'user' in df.columns:
    agent_performance = df.groupby('user').agg({
        'Answered': 'sum',
        'Sale': 'sum'
    }).reset_index()
    
    agent_performance['Conversion %'] = (
        agent_performance['Sale'] / agent_performance['Answered'] * 100
    ).fillna(0).round(2)
    
    agent_performance = agent_performance.sort_values('Sale', ascending=False)
    st.dataframe(agent_performance, use_container_width=True)
else:
    st.info("No agent data available")

st.markdown("---")

# ========== Sales by State ==========
st.subheader("🌍 Sales by State")

if 'state' in df.columns:
    sales_by_state = df[df['Sale'] == 1]['state'].value_counts().reset_index()
    if len(sales_by_state) > 0:
        sales_by_state.columns = ['State', 'Sales']
        st.dataframe(sales_by_state, use_container_width=True)
    else:
        st.info("No sales data available for states")
else:
    st.info("No state data available")

st.markdown("---")

# ========== Sales Details Section ==========
st.subheader("💰 Sales Details - Call Recording")

sales_df = df[df['Sale'] == 1].copy()

if len(sales_df) > 0:
    sales_details = sales_df[[
        'phone_number_dialed', 'user', 'state', 'call_date', 'length_in_sec'
    ]].copy()
    
    sales_details = sales_details.sort_values('call_date', ascending=False)
    sales_details.columns = ['Phone Number', 'Agent', 'State', 'Call Date', 'Duration (sec)']
    
    st.dataframe(sales_details, use_container_width=True)
    
    col_s1, col_s2, col_s3 = st.columns(3)
    
    with col_s1:
        st.metric("Total Sales", len(sales_df))
    with col_s2:
        top_agent = sales_df['user'].value_counts().index[0] if len(sales_df) > 0 else "N/A"
        st.metric("Top Agent", top_agent)
    with col_s3:
        top_state = sales_df['state'].value_counts().index[0] if len(sales_df) > 0 else "N/A"
        st.metric("Top State", top_state)
    
    csv_sales = sales_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download Sales Details CSV",
        data=csv_sales,
        file_name=f"sales_details_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
else:
    st.info("📭 No sales yet in this list. Try another list or improve lead quality.")

st.markdown("---")

# ========== Agent Call Notes ==========
st.subheader("📝 Agent Call Notes")

if len(sales_df) > 0 and 'phone_number_dialed' in sales_df.columns:
    selected_phone = st.selectbox(
        "Select a phone number to view call notes:",
        options=sales_df['phone_number_dialed'].tolist()
    )
    
    call_details = sales_df[sales_df['phone_number_dialed'] == selected_phone].iloc[0]
    
    col_n1, col_n2 = st.columns(2)
    
    with col_n1:
        st.markdown(f"**📞 Phone:** {call_details['phone_number_dialed']}")
        st.markdown(f"**👤 Agent:** {call_details['user']}")
        st.markdown(f"**📍 State:** {call_details['state'] if pd.notna(call_details['state']) else 'N/A'}")
    
    with col_n2:
        st.markdown(f"**⏰ Time:** {call_details['call_date'] if pd.notna(call_details['call_date']) else 'N/A'}")
        st.markdown(f"**⏱️ Duration:** {call_details['length_in_sec']} seconds")
    
    if 'comments' in df.columns:
        st.markdown("---")
        st.markdown("**📋 Call Notes from Agent:**")
        comments = call_details.get('comments', 'No notes available')
        st.info(str(comments) if pd.notna(comments) else "No notes recorded for this call")
elif len(sales_df) == 0:
    st.info("No sales data available to display notes.")
elif 'phone_number_dialed' not in sales_df.columns:
    st.info("Phone number column not available in data.")

st.markdown("---")

# ========== Export Reports Section ==========
st.subheader("📄 Export Reports")

export_cols = [col for col in ['phone_number_dialed', 'state', 'user', 'status', 'Answered', 'Sale', 'AI_Lead', 'AI_Score'] if col in df.columns]
export_df = df[export_cols].copy()

kpi_df = pd.DataFrame({
    "Metric": ["Total Calls", "Answered Calls", "Sales", "Contact Rate %", "Conversion Rate %"],
    "Value": [total_calls, answered, sales, round(contact_rate, 2), round(conversion_rate, 2)]
})

if 'user' in df.columns:
    agent_export = df.groupby('user').agg({
        'Answered': 'sum',
        'Sale': 'sum'
    }).reset_index()
    agent_export['Conversion %'] = (agent_export['Sale'] / agent_export['Answered'] * 100).fillna(0).round(2)
else:
    agent_export = pd.DataFrame()

ai_distribution = df['AI_Lead'].value_counts().reset_index()
ai_distribution.columns = ['Lead Type', 'Count']

col_export1, col_export2 = st.columns(2)

with col_export1:
    csv_data = export_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download CSV Report",
        data=csv_data,
        file_name=f"call_center_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

with col_export2:
    buffer = io.BytesIO()
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        export_df.to_excel(writer, sheet_name='Leads Data', index=False)
        kpi_df.to_excel(writer, sheet_name='KPIs', index=False)
        if not agent_export.empty:
            agent_export.to_excel(writer, sheet_name='Agent Performance', index=False)
        ai_distribution.to_excel(writer, sheet_name='AI Lead Distribution', index=False)
        if 'state' in df.columns and len(df[df['Sale'] == 1]) > 0:
            sales_by_state_export = df[df['Sale'] == 1]['state'].value_counts().reset_index()
            sales_by_state_export.columns = ['State', 'Sales']
            sales_by_state_export.to_excel(writer, sheet_name='Sales by State', index=False)
    
    buffer.seek(0)
    
    st.download_button(
        label="⬇️ Download Excel Report (Multi-Sheet)",
        data=buffer,
        file_name=f"call_center_full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

st.caption(f"📁 Current file: {selected_file} | Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ========== Raw Data (Expander) ==========
with st.expander("🔍 View Raw Data"):
    st.dataframe(df, use_container_width=True)