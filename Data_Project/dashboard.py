import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gc
import plotly.express as px
from sklearn.ensemble import RandomForestClassifier

# ========== إعدادات الصفحة ==========
st.set_page_config(
    page_title="DME Dashboard",
    page_icon="📊",
    layout="wide"
)

# ========== عنوان الصفحة ==========
st.title("🔥DME Dashboard")
st.markdown("---")

# ========== رفع الملف ==========
st.sidebar.header("📁 Upload Your Data")
st.sidebar.caption("🔒 Your file is processed in memory and NOT saved")

uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type=["csv"])

if uploaded_file is not None:
    # حد أقصى لحجم الملف (50 ميجابايت)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    
    if uploaded_file.size > MAX_FILE_SIZE:
        st.error(f"❌ الملف كبير جداً (أقصى حجم 50 ميجابايت). حجم ملفك: {uploaded_file.size / (1024*1024):.1f} MB")
        st.stop()
    
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine="python", encoding="utf-8")
        st.sidebar.success(f"✅ Loaded {len(df)} records (temporary only)")
        st.toast(f"✅ تم تحميل {len(df)} سجل بنجاح!", icon="🎉")
        del uploaded_file
        gc.collect()
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()
else:
    st.info("👈 Please upload a CSV file from the sidebar to get started")
    st.stop()

# ========== 📅 Time Comparison (مقارنة بين فترتين) ==========
st.sidebar.subheader("📅 Time Comparison")
compare_mode = st.sidebar.radio(
    "Compare with:",
    ["No comparison", "Yesterday", "Last 7 days", "Last 30 days"],
    index=0
)

df_original = df.copy()

if compare_mode != "No comparison" and 'call_date' in df.columns:
    df['call_date'] = pd.to_datetime(df['call_date'], errors='coerce')
    latest_date = df['call_date'].max()
    
    if compare_mode == "Yesterday":
        start_date = latest_date - timedelta(days=1)
        end_date = latest_date
        prev_start = start_date - timedelta(days=1)
        prev_end = end_date - timedelta(days=1)
    elif compare_mode == "Last 7 days":
        start_date = latest_date - timedelta(days=7)
        end_date = latest_date
        prev_start = start_date - timedelta(days=7)
        prev_end = end_date - timedelta(days=7)
    else:  # Last 30 days
        start_date = latest_date - timedelta(days=30)
        end_date = latest_date
        prev_start = start_date - timedelta(days=30)
        prev_end = end_date - timedelta(days=30)
    
    current_df = df[(df['call_date'] >= start_date) & (df['call_date'] <= end_date)]
    prev_df = df[(df['call_date'] >= prev_start) & (df['call_date'] <= prev_end)]
    
    current_sales = current_df['Sale'].sum() if 'Sale' in current_df.columns else 0
    prev_sales = prev_df['Sale'].sum() if 'Sale' in prev_df.columns else 0
    
    sales_change = ((current_sales - prev_sales) / prev_sales * 100) if prev_sales > 0 else 0
else:
    current_df = df
    sales_change = 0

# ========== List Quality Analyzer ==========
st.subheader("📋 List Quality Analyzer - DME List Check")

# تحويل أسماء الأعمدة
df.columns = df.columns.str.lower().str.strip()

# 1. Data Completeness
actual_phone_col = None
for col in df.columns:
    if 'phone' in col:
        actual_phone_col = col
        break

required_found = []
if actual_phone_col:
    required_found.append('phone')
if 'full_name' in df.columns:
    required_found.append('full_name')
if 'age' in df.columns:
    required_found.append('age')
if 'state' in df.columns or 'st' in df.columns:
    required_found.append('state')
if 'zip_code' in df.columns or 'zip' in df.columns:
    required_found.append('zip')
    
completeness_score = len(required_found) / 5 * 10

# 2. Insurance Check
insurance_cols = [col for col in df.columns if 'insurance' in col or 'medicare' in col or 'ppo' in col or 'hmo' in col]
insurance_score = 10 if insurance_cols else 0

# 3. Age Analysis
if 'age' in df.columns:
    df['age'] = pd.to_numeric(df['age'], errors='coerce')
    age_50_plus = df[df['age'] >= 50].shape[0]
    age_70_plus = df[df['age'] >= 70].shape[0]
    age_score = min(10, (age_50_plus / len(df) * 10)) if len(df) > 0 else 0
else:
    age_50_plus = 0
    age_70_plus = 0
    age_score = 0

# 4. Pain Condition
pain_keywords = ['knee', 'back', 'arthritis', 'diabetes', 'pain', 'chronic', 'sleep apnea', 'mobility', 'condition']
pain_cols = [col for col in df.columns if any(kw in col for kw in pain_keywords)]
pain_score = 10 if pain_cols else 0

# 5. Freshness
date_cols = [col for col in df.columns if 'date' in col or 'created' in col or 'timestamp' in col]
freshness_score = 10 if date_cols else 0

# 6. Duplicate Check
if actual_phone_col:
    duplicates = df[df.duplicated(subset=[actual_phone_col], keep=False)]
    duplicate_count = len(duplicates)
    duplicate_score = max(0, 10 - (duplicate_count / len(df) * 20)) if len(df) > 0 else 10
else:
    duplicate_count = 0
    duplicate_score = 10

# 7. Missing Data
missing_pct = df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100 if len(df) > 0 else 0
missing_score = max(0, 10 - (missing_pct / 10))

# 8. Phone Quality
if actual_phone_col:
    df['phone_str'] = df[actual_phone_col].astype(str).str.replace('[^0-9]', '', regex=True)
    valid_phones = df[df['phone_str'].str.len() == 10].shape[0]
    phone_score = (valid_phones / len(df)) * 10 if len(df) > 0 else 0
else:
    valid_phones = 0
    phone_score = 0

# 9. States Analysis
top_dme_states = ['FL', 'TX', 'AZ', 'CA', 'NV', 'NC', 'SC', 'GA', 'TN', 'OH', 'NY', 'PA', 'IL', 'MI', 'NJ']
if 'state' in df.columns:
    df['state_upper'] = df['state'].astype(str).str.upper().str[:2]
    strong_state_count = df[df['state_upper'].isin(top_dme_states)].shape[0]
    state_score = (strong_state_count / len(df)) * 10 if len(df) > 0 else 0
elif 'st' in df.columns:
    df['state_upper'] = df['st'].astype(str).str.upper().str[:2]
    strong_state_count = df[df['state_upper'].isin(top_dme_states)].shape[0]
    state_score = (strong_state_count / len(df)) * 10 if len(df) > 0 else 0
else:
    strong_state_count = 0
    state_score = 0

# 10. Intent Indicators
intent_keywords = ['interested', 'requested', 'submitted', 'pain relief', 'callback', 'quote', 'info', 'intent', 'lead_score']
intent_cols = [col for col in df.columns if any(kw in col for kw in intent_keywords)]
intent_score = 10 if intent_cols else 0

# ========== المجموع النهائي ==========
weights = {
    'completeness': 0.10,
    'insurance': 0.15,
    'age': 0.15,
    'pain': 0.15,
    'freshness': 0.10,
    'duplicate': 0.05,
    'missing': 0.05,
    'phone': 0.05,
    'state': 0.05,
    'intent': 0.15
}

final_score = (
    completeness_score * weights['completeness'] +
    insurance_score * weights['insurance'] +
    age_score * weights['age'] +
    pain_score * weights['pain'] +
    freshness_score * weights['freshness'] +
    duplicate_score * weights['duplicate'] +
    missing_score * weights['missing'] +
    phone_score * weights['phone'] +
    state_score * weights['state'] +
    intent_score * weights['intent']
)

# ========== عرض النتائج ==========
st.markdown("### 📊 List Quality Report")

if final_score >= 7:
    verdict = "🟢 Strong List"
    expectation = "High Conversion Expected"
    recommendation = "✅ START - Good to go"
    rec_color = "green"
elif final_score >= 5:
    verdict = "🟡 Average List"
    expectation = "Medium Conversion Expected"
    recommendation = "⚠️ TEST - Run 100 calls first"
    rec_color = "orange"
else:
    verdict = "🔴 Weak List"
    expectation = "Low Conversion Expected"
    recommendation = "❌ SKIP - Red flags detected"
    rec_color = "red"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Overall Score", f"{final_score:.1f}/10")
col2.metric("Verdict", verdict)
col3.metric("Expectation", expectation)
col4.markdown(f"<h3 style='color: {rec_color};'>{recommendation}</h3>", unsafe_allow_html=True)

st.markdown("---")

# ========== تفاصيل التحليل ==========
with st.expander("🔍 View Detailed Analysis (10 Metrics)"):
    st.markdown("**1. Data Completeness:**")
    st.progress(completeness_score/10)
    st.caption(f"Score: {completeness_score:.1f}/10 | Found: {', '.join(required_found) if required_found else 'Minimal data'}")
    
    st.markdown("**2. Insurance Check:**")
    st.progress(insurance_score/10)
    st.caption(f"Score: {insurance_score:.1f}/10 | Insurance column {'✅ found' if insurance_cols else '❌ missing'}")
    
    st.markdown("**3. Age Analysis:**")
    st.progress(age_score/10)
    st.caption(f"Score: {age_score:.1f}/10 | {age_50_plus} leads 50+")
    
    st.markdown("**4. Pain Condition:**")
    st.progress(pain_score/10)
    st.caption(f"Score: {pain_score:.1f}/10 | Pain column {'✅ found' if pain_cols else '❌ missing'}")
    
    st.markdown("**5. Freshness:**")
    st.progress(freshness_score/10)
    st.caption(f"Score: {freshness_score:.1f}/10 | Date column {'✅ found' if date_cols else '❌ missing'}")
    
    st.markdown("**6. Duplicate Check:**")
    st.progress(duplicate_score/10)
    st.caption(f"Score: {duplicate_score:.1f}/10 | {duplicate_count} duplicates")
    
    st.markdown("**7. Missing Data:**")
    st.progress(missing_score/10)
    st.caption(f"Score: {missing_score:.1f}/10 | {missing_pct:.1f}% missing")
    
    st.markdown("**8. Phone Quality:**")
    st.progress(phone_score/10)
    st.caption(f"Score: {phone_score:.1f}/10 | {valid_phones}/{len(df)} valid phones")
    
    st.markdown("**9. States Analysis:**")
    st.progress(state_score/10)
    st.caption(f"Score: {state_score:.1f}/10 | {strong_state_count} leads from top DME states")
    
    st.markdown("**10. Intent Indicators:**")
    st.progress(intent_score/10)
    st.caption(f"Score: {intent_score:.1f}/10 | Intent column {'✅ found' if intent_cols else '❌ missing'}")

st.markdown("---")

# ========== Critical Issues ==========
st.subheader("⚠️ Critical Issues & Recommendations")

issues = []
if insurance_score == 0:
    issues.append("❌ **No Insurance column** - Critical for DME")
if pain_score == 0:
    issues.append("❌ **No Pain/Medical Condition column**")
if freshness_score == 0:
    issues.append("❌ **No Lead Date column**")
if intent_score == 0:
    issues.append("⚠️ **No Intent column**")
if age_score < 5:
    issues.append(f"⚠️ **Age issue:** Only {age_50_plus}/{len(df)} leads 50+")
if state_score < 4:
    issues.append(f"⚠️ **State issue:** Only {strong_state_count}/{len(df)} from top DME states")

if issues:
    for issue in issues:
        if "CRITICAL" in issue or "❌" in issue:
            st.error(issue)
        else:
            st.warning(issue)
else:
    st.success("✅ No critical issues detected!")

st.markdown("---")

# ========== تنظيف البيانات الأساسية ==========
def clean_data(df):
    df = df.copy()
    
    if 'status' in df.columns:
        df['status'] = df['status'].astype(str).str.strip().str.upper()
        df['Answered'] = df['status'].apply(
            lambda x: 0 if x in ['NA', 'NO ANSWER', 'DROP', 'DROP?', 'EMPTY'] else 1
        )
        df['Sale'] = df['status'].apply(lambda x: 1 if x == 'SALE' else 0)
    else:
        df['Answered'] = 0
        df['Sale'] = 0
    
    if 'call_date' in df.columns:
        df['call_date'] = pd.to_datetime(df['call_date'], errors='coerce')
        df['hour'] = df['call_date'].dt.hour
    else:
        df['hour'] = 12
    
    if 'length_in_sec' in df.columns:
        df['length_in_sec'] = pd.to_numeric(df['length_in_sec'], errors='coerce').fillna(0)
    else:
        df['length_in_sec'] = 0
    
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

# ========== KPIs مع المقارنة ==========
total_calls = len(df)
answered = df['Answered'].sum()
sales = df['Sale'].sum()
contact_rate = (answered / total_calls) * 100 if total_calls > 0 else 0
conversion_rate = (sales / answered) * 100 if answered > 0 else 0

st.subheader("📈 Key Performance Indicators")

# عرض نسبة التغيير لو موجودة
if compare_mode != "No comparison" and sales_change != 0:
    delta_str = f"{sales_change:+.1f}% vs previous"
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Calls", f"{total_calls:,}")
    col2.metric("Answered Calls", f"{answered:,}")
    col3.metric("Sales", f"{sales:,}", delta=delta_str)
    col4.metric("Contact Rate", f"{contact_rate:.1f}%")
    col5.metric("Conversion Rate", f"{conversion_rate:.1f}%")
else:
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Calls", f"{total_calls:,}")
    col2.metric("Answered Calls", f"{answered:,}")
    col3.metric("Sales", f"{sales:,}")
    col4.metric("Contact Rate", f"{contact_rate:.1f}%")
    col5.metric("Conversion Rate", f"{conversion_rate:.1f}%")
st.markdown("---")

# ========== List Quality Assessment (Performance) ==========
st.subheader("📋 List Quality Assessment")
list_answered_rate = (answered / total_calls) * 100
list_sales_rate = (sales / total_calls) * 100
dnc_count = df['status'].isin(['DNC', 'DO NOT CALL']).sum() if 'status' in df.columns else 0
list_dnc_rate = (dnc_count / total_calls) * 100

quality_score = (list_answered_rate * 0.4) + (list_sales_rate * 0.5) + max(0, (100 - list_dnc_rate) * 0.1)

if quality_score >= 70:
    quality_rating = "🟢 Excellent List! 🔥"
elif quality_score >= 50:
    quality_rating = "🟡 Good List 👍"
elif quality_score >= 30:
    quality_rating = "🟠 Average List 📊"
else:
    quality_rating = "🔴 Poor List ⚠️"

col_q1, col_q2, col_q3, col_q4 = st.columns(4)
col_q1.metric("Answer Rate", f"{list_answered_rate:.1f}%")
col_q2.metric("Sales Rate", f"{list_sales_rate:.1f}%")
col_q3.metric("DNC Rate", f"{list_dnc_rate:.1f}%")
col_q4.markdown(f"### {quality_rating}")
st.caption(f"Quality Score: {quality_score:.1f}/100")
st.markdown("---")

# ========== List Recommendation ==========
st.subheader("🎯 List Recommendation")

if quality_score >= 50:
    recommendation = "✅ **RECOMMENDATION: CONTINUE**"
    rec_color = "green"
    rec_detail = "This list is performing well. Keep calling and monitor daily."
elif quality_score >= 30:
    recommendation = "⚠️ **RECOMMENDATION: REVIEW**"
    rec_color = "orange"
    rec_detail = "This list needs improvement. Review the 'What to Remove' section below."
else:
    recommendation = "❌ **RECOMMENDATION: STOP**"
    rec_color = "red"
    rec_detail = "This list is draining your team's time. Remove bad numbers and change strategy."

st.markdown(f"<h3 style='color: {rec_color};'>{recommendation}</h3>", unsafe_allow_html=True)
st.info(rec_detail)
st.markdown("---")

# ========== 🔔 Smart Alerts ==========
st.subheader("🔔 Smart Alerts")

alerts = []

if sales < 5 and total_calls > 100:
    alerts.append("⚠️ **Alert:** Sales are very low today compared to call volume")

if quality_score < 30:
    alerts.append("🚨 **Urgent Alert:** List quality is critical! Stop using this list.")

if list_dnc_rate > 20:
    alerts.append(f"⚠️ **Warning:** DNC rate is {list_dnc_rate:.0f}%. Consider scrubbing your list.")

if conversion_rate < 5 and total_calls > 50:
    alerts.append("⚠️ **Warning:** Conversion rate is very low. Review agent scripts.")

if alerts:
    for alert in alerts:
        if "Urgent" in alert:
            st.error(alert)
        elif "Warning" in alert:
            st.warning(alert)
        else:
            st.info(alert)
else:
    st.info("✅ No alerts at this time. Everything looks good!")
st.markdown("---")

# ========== 💡 AI Smart Tips ==========
st.subheader("💡 AI Smart Tips")

tips = []

if conversion_rate > 10:
    tips.append("🔥 **Excellent conversion rate!** Consider increasing call volume to maximize sales.")
elif conversion_rate > 5:
    tips.append("👍 **Good conversion rate.** Keep up the current strategy.")
else:
    tips.append("📉 **Low conversion rate.** Review agent scripts or lead quality.")

if list_dnc_rate > 20:
    tips.append("🚫 **High DNC rate.** Your list needs scrubbing. Remove DNC numbers immediately.")
elif list_dnc_rate > 10:
    tips.append("⚠️ **Moderate DNC rate.** Monitor this list closely.")

if 'hour' in df.columns:
    best_hour = df.groupby('hour')['Sale'].sum().idxmax()
    tips.append(f"⏰ **Best time to call:** {best_hour}:00 - {best_hour+1}:00 (based on sales history)")

if len(df[df['Sale'] == 1]) > 0:
    top_agent = df[df['Sale'] == 1]['user'].mode()[0] if 'user' in df.columns else "Unknown"
    tips.append(f"🏆 **Top performer:** {top_agent} - Consider sharing their script with the team.")

for tip in tips:
    st.info(tip)
st.markdown("---")

# ========== 🏆 Agent Leaderboard (لوحة الشرف) ==========
st.subheader("🏆 Agent Leaderboard")

if 'user' in df.columns:
    agent_perf = df.groupby('user').agg({
        'Answered': 'sum',
        'Sale': 'sum'
    }).reset_index()
    agent_perf['Conversion %'] = (agent_perf['Sale'] / agent_perf['Answered'] * 100).fillna(0).round(2)
    agent_perf = agent_perf.sort_values('Sale', ascending=False)
    
    # عرض التوب 5 مع ميداليات
    for i, row in agent_perf.head(5).iterrows():
        if i == 0:
            medal = "🥇"
            color = "#FFD700"
        elif i == 1:
            medal = "🥈"
            color = "#C0C0C0"
        elif i == 2:
            medal = "🥉"
            color = "#CD7F32"
        else:
            medal = "📌"
            color = "#888"
        
        st.markdown(
            f"<div style='background-color: {color}20; padding: 10px; border-radius: 10px; margin: 5px 0;'>"
            f"{medal} <b>{row['user']}</b> - {row['Sale']} sales | Conv: {row['Conversion %']}%"
            f"</div>",
            unsafe_allow_html=True
        )
else:
    st.info("No agent data available for leaderboard")
st.markdown("---")

# ========== Charts ==========
st.subheader("📊 Performance Charts")
col_ch1, col_ch2 = st.columns(2)

with col_ch1:
    st.markdown("**📈 Sales by Hour**")
    if 'hour' in df.columns:
        sales_by_hour = df.groupby('hour')['Sale'].sum()
        st.bar_chart(sales_by_hour)

with col_ch2:
    st.markdown("**📞 Answered Calls by Hour**")
    if 'hour' in df.columns:
        answered_by_hour = df.groupby('hour')['Answered'].sum()
        st.line_chart(answered_by_hour)
st.markdown("---")

# ========== Dispositions Summary ==========
st.subheader("📊 Dispositions Summary")

if 'status' in df.columns:
    disposition_summary = df['status'].value_counts().reset_index()
    disposition_summary.columns = ['Status', 'Count']
    disposition_summary['Percentage'] = (disposition_summary['Count'] / len(df) * 100).round(1)
    
    st.dataframe(disposition_summary, use_container_width=True)
    st.bar_chart(disposition_summary.set_index('Status')['Count'])
    
    csv_dispo = disposition_summary.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download Dispositions CSV", csv_dispo, f"dispositions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")
else:
    st.info("No status data available")
st.markdown("---")

# ========== What to Remove ==========
st.subheader("🧹 What to Remove Before Calling")

bad_statuses = ['DNC', 'DO NOT CALL', 'DROP', 'DROP?', 'NA', 'NO ANSWER', 'EMPTY']
bad_numbers = df[df['status'].isin(bad_statuses)] if 'status' in df.columns else pd.DataFrame()
duplicate_numbers = df[df.duplicated(subset=['phone_number_dialed'], keep=False)] if 'phone_number_dialed' in df.columns else pd.DataFrame()
short_calls = df[df['length_in_sec'] < 30] if 'length_in_sec' in df.columns else pd.DataFrame()
no_answer = df[df['status'] == 'NO ANSWER'] if 'status' in df.columns else pd.DataFrame()

col_r1, col_r2 = st.columns(2)

with col_r1:
    st.markdown("**🚫 Remove These Numbers:**")
    removal_items = []
    if len(bad_numbers) > 0:
        removal_items.append(f"- ❌ **DNC / Do Not Call:** {len(bad_numbers)} numbers")
    if len(duplicate_numbers) > 0:
        dup_count = len(duplicate_numbers['phone_number_dialed'].unique()) if 'phone_number_dialed' in duplicate_numbers.columns else len(duplicate_numbers)
        removal_items.append(f"- 🔄 **Duplicate numbers:** {dup_count} unique numbers")
    if len(no_answer) > 0:
        removal_items.append(f"- 📵 **No Answer:** {len(no_answer)} calls")
    
    if removal_items:
        for item in removal_items:
            st.warning(item)
    else:
        st.success("✅ No obvious bad numbers detected")

with col_r2:
    st.markdown("**⏱️ Calls Wasting Time:**")
    if len(short_calls) > 0:
        st.warning(f"- 📞 **Short calls (<30 sec):** {len(short_calls)} calls")
    else:
        st.info("No unusually short calls detected")

st.markdown("**💡 Remove these numbers before your next campaign to save time and increase conversion rate.**")
st.markdown("---")

# ========== AI Lead Analysis ==========
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
st.markdown("---")

# ========== Agent Performance Table ==========
st.subheader("👨‍💼 Agent Performance Table")
if 'user' in df.columns:
    st.dataframe(agent_perf, use_container_width=True)
else:
    st.info("No agent data available")
st.markdown("---")

# ========== AI Sales Predictor ==========
st.subheader("🎯 AI Sales Predictor - Who Will Buy Next?")

try:
    predictor_df = df[df['Answered'] == 1].copy()
    predictor_df['target'] = predictor_df['Sale']
    
    features = ['length_in_sec', 'hour']
    predictor_df = predictor_df.dropna(subset=features + ['target'])
    
    if len(predictor_df) > 20 and predictor_df['target'].nunique() > 1:
        X = predictor_df[features]
        y = predictor_df['target']
        
        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(X, y)
        
        non_buyers = df[(df['Answered'] == 1) & (df['Sale'] == 0)].copy()
        
        if len(non_buyers) > 0:
            X_pred = non_buyers[features].fillna(0)
            probabilities = model.predict_proba(X_pred)[:, 1]
            
            non_buyers['Purchase_Probability'] = (probabilities * 100).round(1)
            top_potential = non_buyers.nlargest(5, 'Purchase_Probability')
            
            st.markdown("**🔥 Top 5 Leads Most Likely to Buy:**")
            st.dataframe(
                top_potential[['phone_number_dialed', 'state', 'Purchase_Probability']],
                use_container_width=True
            )
        else:
            st.info("No potential leads found")
    else:
        st.info("Not enough data for AI prediction (need more answered calls)")
except Exception as e:
    st.info(f"AI Predictor needs more data to work properly")
st.markdown("---")

# ========== Agent Disposition Details ==========
st.subheader("📋 Agent Disposition Details")

if 'user' in df.columns and 'status' in df.columns:
    disposition_table = df.groupby(['user', 'status']).size().reset_index(name='count')
    pivot_table = disposition_table.pivot(index='user', columns='status', values='count').fillna(0).astype(int)
    pivot_table['Total Calls'] = pivot_table.sum(axis=1)
    cols = ['Total Calls'] + [col for col in pivot_table.columns if col != 'Total Calls']
    pivot_table = pivot_table[cols]
    
    st.dataframe(pivot_table, use_container_width=True)
    
    csv_disp = disposition_table.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download Agent Disposition CSV", csv_disp, f"agent_disposition_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")
else:
    st.info("No agent or status data available")
st.markdown("---")

# ========== Sales Heatmap ==========
st.subheader("🗺️ Sales Heatmap by State")

if 'state' in df.columns and len(df[df['Sale'] == 1]) > 0:
    try:
        state_sales = df[df['Sale'] == 1]['state'].value_counts().reset_index()
        state_sales.columns = ['state', 'sales']
        
        fig = px.choropleth(
            state_sales,
            locations='state',
            locationmode='USA-states',
            color='sales',
            scope='usa',
            title='Sales Distribution by State',
            color_continuous_scale='Reds',
            labels={'sales': 'Number of Sales'}
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info("Heatmap requires plotly library. Run: pip install plotly")
else:
    st.info("No sales data available for heatmap")
st.markdown("---")

# ========== Sales by State Table ==========
st.subheader("🌍 Sales by State")
if 'state' in df.columns:
    sales_by_state = df[df['Sale'] == 1]['state'].value_counts().reset_index()
    if len(sales_by_state) > 0:
        sales_by_state.columns = ['State', 'Sales']
        st.dataframe(sales_by_state, use_container_width=True)
    else:
        st.info("No sales data available")
else:
    st.info("No state data available")
st.markdown("---")

# ========== Sales Details ==========
st.subheader("💰 Sales Details")
sales_df = df[df['Sale'] == 1]
if len(sales_df) > 0:
    sales_details = sales_df[['phone_number_dialed', 'user', 'state', 'call_date', 'length_in_sec']].copy()
    sales_details = sales_details.sort_values('call_date', ascending=False)
    sales_details.columns = ['Phone', 'Agent', 'State', 'Date', 'Duration']
    st.dataframe(sales_details, use_container_width=True)
    
    csv_sales = sales_df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download Sales CSV", csv_sales, f"sales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")
else:
    st.info("📭 No sales yet")
st.markdown("---")

# ========== Auto Summary Report ==========
st.subheader("📝 Auto Summary Report")

if total_calls > 0:
    top_agent_val = agent_perf.iloc[0]['user'] if len(agent_perf) > 0 else "N/A"
    top_sales_val = agent_perf.iloc[0]['Sale'] if len(agent_perf) > 0 else 0
    
    if conversion_rate > 10:
        perf_text = "great"
    elif conversion_rate > 5:
        perf_text = "okay"
    else:
        perf_text = "below average"
    
    summary_text = f"""
### 📊 Executive Summary

**Overall Performance:**
- Today we had **{total_calls:,} calls** with **{sales} sales**.
- Conversion rate is **{conversion_rate:.1f}%**, which is **{perf_text}**.

**Top Performer:**
- **{top_agent_val}** is the top agent with **{top_sales_val} sales**.

**List Quality:**
- The current list is **{quality_rating.split()[1]}** with a quality score of **{quality_score:.0f}/100**.

**Recommendation:**
- {'✅ Continue with this list' if quality_score >= 50 else '⚠️ Review this list before continuing' if quality_score >= 30 else '❌ Stop using this list immediately'}.

**Best Time to Call:**
- Based on the chart above, focus calls during peak hours.

---
*Report generated automatically at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    st.markdown(summary_text)
    st.download_button("📋 Copy Summary Report", summary_text, f"summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "text/plain")
else:
    st.info("No data available for summary report")
st.markdown("---")

# ========== Export Full Report ==========
st.subheader("📄 Export Full Report")
export_df = df[[
    'phone_number_dialed', 'state', 'user', 'status', 
    'Answered', 'Sale', 'AI_Lead', 'AI_Score'
]].copy() if all(col in df.columns for col in ['phone_number_dialed', 'state', 'user', 'status', 'Answered', 'Sale', 'AI_Lead', 'AI_Score']) else df.copy()

csv_full = export_df.to_csv(index=False).encode('utf-8')
st.download_button("⬇️ Download Full CSV Report", csv_full, f"full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")

st.caption(f"🔒 Data processed temporarily | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ========== Raw Data ==========
with st.expander("🔍 View Raw Data"):
    st.dataframe(df, use_container_width=True)

# ========== Filter Valid Leads ==========
st.subheader("🎯 Filter Valid Leads - Ready to Call")

col_f1, col_f2 = st.columns(2)

with col_f1:
    if 'age' in df.columns:
        age_min = st.number_input("Minimum Age", min_value=18, max_value=100, value=50)
    else:
        age_min = 50
        st.info("No age column found")
    
    if 'state' in df.columns or 'st' in df.columns:
        state_col = 'state' if 'state' in df.columns else 'st'
        all_states = sorted(df[state_col].dropna().unique())
        selected_states = st.multiselect("Select States", all_states, default=[])
    else:
        selected_states = []

with col_f2:
    insurance_col = None
    for col in df.columns:
        if any(kw in col for kw in ['insurance', 'ins', 'coverage', 'payor']):
            insurance_col = col
            break
    
    if insurance_col:
        all_ins = sorted(df[insurance_col].dropna().unique())
        selected_ins = st.multiselect("Select Insurance Type", all_ins, default=[])
    else:
        selected_ins = []
        st.info("No insurance column found")
    
    keyword_filter = st.text_input("Filter by keyword (e.g., knee, back, diabetes)", "")

filtered_df = df.copy()

if 'age' in df.columns:
    filtered_df = filtered_df[filtered_df['age'] >= age_min]

if selected_states:
    filtered_df = filtered_df[filtered_df[state_col].isin(selected_states)]

if selected_ins and insurance_col:
    filtered_df = filtered_df[filtered_df[insurance_col].isin(selected_ins)]

if keyword_filter:
    keyword_lower = keyword_filter.lower()
    text_cols = filtered_df.select_dtypes(include=['object']).columns
    mask = False
    for col in text_cols:
        mask = mask | filtered_df[col].astype(str).str.lower().str.contains(keyword_lower, na=False)
    filtered_df = filtered_df[mask]

st.markdown("---")
st.markdown("### 📊 Filter Results")

col_r1, col_r2, col_r3 = st.columns(3)
col_r1.metric("Total Leads in List", len(df))
col_r2.metric("Valid Leads (After Filter)", len(filtered_df))
col_r3.metric("Percentage", f"{len(filtered_df)/len(df)*100:.1f}%" if len(df) > 0 else "0%")

if len(filtered_df) > 0:
    st.markdown("### 📞 Valid Leads Details")
    display_cols = []
    for col in ['phone_number', 'phone_number_dialed', 'full_name', 'first_name', 'name', 'age', 'state', 'st', 'city', 'insurance', 'status']:
        if col in filtered_df.columns:
            display_cols.append(col)
    
    if not display_cols:
        display_cols = filtered_df.columns[:5].tolist()
    
    st.dataframe(filtered_df[display_cols], use_container_width=True)
    
    csv_valid = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download Valid Leads CSV", csv_valid, f"valid_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")
else:
    st.warning("⚠️ No leads match the selected filters.")
