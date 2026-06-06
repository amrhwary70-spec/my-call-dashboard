import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

# ========== 1. قراءة البيانات ==========
df = pd.read_csv("data.csv", sep="\t", encoding="utf-8", engine="python")

# ========== 2. تنظيف البيانات ==========
df['status'] = df['status'].astype(str).str.strip().str.upper()
df['Answered'] = df['status'].apply(lambda x: 0 if x in ['NA', 'NO ANSWER', 'DROP'] else 1)
df['Sale'] = df['status'].apply(lambda x: 1 if x == 'SALE' else 0)

# ========== 3. حساب الـ KPIs الأساسية ==========
total_calls = len(df)
answered_calls = df['Answered'].sum()
sales = df['Sale'].sum()

contact_rate = (answered_calls / total_calls) * 100 if total_calls > 0 else 0
conversion_rate = (sales / answered_calls) * 100 if answered_calls > 0 else 0

print("\n===== KPI REPORT =====")
print("Total Calls:", total_calls)
print("Answered:", answered_calls)
print("Sales:", sales)
print("Contact Rate:", round(contact_rate, 2), "%")
print("Conversion Rate:", round(conversion_rate, 2), "%")

# ========== 4. أفضل الوكلاء والولايات ==========
print("\nTop Agents:")
print(df.groupby('user')['Sale'].sum().sort_values(ascending=False))

print("\nTop States:")
print(df[df['Sale'] == 1]['state'].value_counts())

# ========== 5. حساب العمر من تاريخ الميلاد ==========
df['date_of_birth'] = pd.to_datetime(df['date_of_birth'], errors='coerce')
today = datetime.today()
df['age'] = df['date_of_birth'].apply(
    lambda x: today.year - x.year if pd.notnull(x) else None
)

print("\nSales by Age Group:")
print(df[df['Sale'] == 1]['age'].value_counts().sort_index())

# ========== 6. تصنيف اللييدات (Lead Scoring) ==========
df['lead_score'] = (
    df['Answered'] * 2 +
    df['Sale'] * 5 +
    (df['length_in_sec'] > 60).astype(int)
)

def classify(score):
    if score >= 6:
        return "Hot Lead 🔥"
    elif score >= 3:
        return "Warm Lead ⚡"
    else:
        return "Cold Lead ❄️"

df['lead_type'] = df['lead_score'].apply(classify)

print("\nLead Distribution:")
print(df['lead_type'].value_counts())

# ========== 7. تحليل الساعات المثالية للاتصال ==========
df['call_date'] = pd.to_datetime(df['call_date'], errors='coerce')
df['hour'] = df['call_date'].dt.hour

best_hours_sales = df.groupby('hour')['Sale'].sum().sort_values(ascending=False)
best_hours_answered = df.groupby('hour')['Answered'].sum().sort_values(ascending=False)

print("\nBest Hours for Sales:")
print(best_hours_sales.head(5))

print("\nBest Hours for Contact:")
print(best_hours_answered.head(5))

# ========== 8. رسومات بيانية ==========
plt.figure(figsize=(10,5))
plt.plot(df.groupby('hour')['Answered'].sum().index,
         df.groupby('hour')['Answered'].sum().values, marker='o')
plt.title("Best Call Hours (Answered Calls)")
plt.xlabel("Hour of Day")
plt.ylabel("Answered Calls")
plt.grid()
plt.show()

plt.figure(figsize=(10,5))
plt.bar(df.groupby('hour')['Sale'].sum().index,
        df.groupby('hour')['Sale'].sum().values)
plt.title("Sales by Hour")
plt.xlabel("Hour")
plt.ylabel("Sales")
plt.show()

# ========== 9. Machine Learning نموذج تنبؤ ==========
features = df[['Answered', 'length_in_sec', 'hour']].fillna(0)
target = df['Sale']

X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)

model = DecisionTreeClassifier(max_depth=4, random_state=42)
model.fit(X_train, y_train)

print("\nModel Accuracy:", round(model.score(X_test, y_test) * 100, 2), "%")

# ========== 10. إضافة احتمالية البيع لكل لييد ==========
df['Sale_Probability'] = model.predict_proba(features)[:, 1]

def lead_ai(prob):
    if prob >= 0.7:
        return "🔥 Hot AI Lead"
    elif prob >= 0.4:
        return "⚡ Warm AI Lead"
    else:
        return "❄️ Cold AI Lead"

df['AI_Lead'] = df['Sale_Probability'].apply(lead_ai)

print("\nAI Lead Distribution:")
print(df['AI_Lead'].value_counts())

# ========== 11. عرض أعلى 10 لييدات حسب الذكاء الاصطناعي ==========
print("\nTop 10 AI Leads:")
print(df.sort_values(by='Sale_Probability', ascending=False)[['phone_number_dialed', 'state', 'Sale_Probability']].head(10))
df = pd.read_csv("data.csv", sep="\t", encoding="utf-8", engine="python")
# ========== Combine Multiple Files ==========
st.sidebar.subheader("🔗 Combine Files")

files_to_combine = st.sidebar.multiselect(
    "Select files to combine",
    files,
    default=[]
)

if st.sidebar.button("Combine Selected Files") and files_to_combine:
    combined_dfs = []
    for f in files_to_combine:
        temp_df = pd.read_csv(f, sep=None, engine="python", encoding="utf-8")
        temp_df['source_file'] = f  # add source column
        combined_dfs.append(temp_df)
    
    df = pd.concat(combined_dfs, ignore_index=True)
    st.sidebar.success(f"✅ Combined {len(files_to_combine)} files: {len(df)} rows")
    
    # override the selection
    selected_file = "🔗 COMBINED FILES"