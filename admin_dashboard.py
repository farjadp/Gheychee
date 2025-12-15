import streamlit as st
import pandas as pd
import firebase_config as fb
import plotly.express as px

st.set_page_config(page_title="Gheychee Admin", layout="wide")

st.title("✂️ Gheychee Bot Admin Dashboard")

if not fb.db:
    st.error("❌ Database connection failed. Please check `service_account.json`.")
    st.stop()

# --- Load Data ---
@st.cache_data(ttl=60)
def load_data():
    users_ref = fb.db.collection('users')
    logs_ref = fb.db.collection('logs')
    
    users = [doc.to_dict() | {'id': doc.id} for doc in users_ref.stream()]
    logs = [doc.to_dict() | {'id': doc.id} for doc in logs_ref.order_by('timestamp', direction=fb.firestore.Query.DESCENDING).limit(500).stream()]
    
    return pd.DataFrame(users), pd.DataFrame(logs)

users_df, logs_df = load_data()

# --- Metrics ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Users", len(users_df))
col2.metric("Total Requests (Saved Logs)", len(logs_df))
if not logs_df.empty:
    success_rate = (logs_df['status'] == 'success').mean() * 100
    col3.metric("Success Rate", f"{success_rate:.1f}%")

# --- Users Table ---
st.subheader("👥 Users")
if not users_df.empty:
    st.dataframe(users_df[['id', 'tier', 'joined_at', 'username']])
    
    # User Management
    with st.expander("Manage User Tier"):
        uid = st.text_input("User ID to Update")
        new_tier = st.selectbox("Select Tier", ["free", "premium", "super"])
        if st.button("Update Tier"):
            if uid:
                fb.db.collection('users').document(uid).update({'tier': new_tier})
                st.success(f"User {uid} updated to {new_tier}")
                st.cache_data.clear()

# --- Logs Analysis ---
st.subheader("📋 Recent Activity")
if not logs_df.empty:
    # Convert timestamp
    logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'])
    
    st.dataframe(logs_df[['timestamp', 'user_id', 'platform', 'status', 'link']])

    # Charts
    st.subheader("📊 Analytics")
    c1, c2 = st.columns(2)
    
    with c1:
        status_counts = logs_df['status'].value_counts().reset_index()
        fig1 = px.pie(status_counts, values='count', names='status', title='Request Status Distribution')
        st.plotly_chart(fig1, use_container_width=True)
        
    with c2:
        platform_counts = logs_df['platform'].value_counts().reset_index()
        fig2 = px.bar(platform_counts, x='platform', y='count', title='Popular Platforms')
        st.plotly_chart(fig2, use_container_width=True)

else:
    st.info("No logs available yet.")
