import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from streamlit_lottie import st_lottie
import requests
import numpy as np

@st.cache_data
def load_lottie_url(url: str):
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    return None

# Page config
st.set_page_config(page_title="YouTube Trending Analytics", page_icon="📊", layout="wide")

# Load Lottie animation
lottie_json = load_lottie_url("https://assets2.lottiefiles.com/packages/lf20_j1adxtyb.json")

# Tabs
tabs = st.tabs(["📈 Dashboard", "🎥 Interactive Video Explorer", "📊 Pro Insights", "🧑‍💻 About"])

# Main Dashboard
with tabs[0]:
    st.title("📈 YouTube Trending Analytics Dashboard")

    if lottie_json:
        st_lottie(lottie_json, height=150)
    st.markdown("Dive into YouTube trending insights with a **dark premium UI** and **subtle animations**.")

    uploaded_file = st.sidebar.file_uploader("📥 Upload YouTube Trending CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file, encoding='latin1')
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Parse date columns
        for col in ['trending_date', 'publish_time']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                if df[col].dt.tz is not None:
                    df[col] = df[col].dt.tz_localize(None)

        # Filters
        with st.sidebar:
            if 'channel_title' in df.columns:
                channels = df['channel_title'].dropna().unique().tolist()
                selected = st.multiselect("🎞 Select Channels", sorted(channels), default=channels[:5])
                df = df[df['channel_title'].isin(selected)]

            for col in ['trending_date', 'publish_time']:
                if col in df.columns:
                    min_d, max_d = df[col].min(), df[col].max()
                    dr = st.date_input(col.replace('_', ' ').title(), (min_d, max_d), min_value=min_d, max_value=max_d)
                    df = df[(df[col] >= pd.to_datetime(dr[0])) & (df[col] <= pd.to_datetime(dr[1]))]
                    break

            view_col = next((c for c in ['view_count', 'views'] if c in df.columns), None)
            if view_col:
                vmin, vmax = int(df[view_col].min()), int(df[view_col].max())
                vr = st.slider("🔍 Filter by Views", vmin, vmax, (vmin, vmax), step=max(1, (vmax-vmin)//100))
                df = df[(df[view_col] >= vr[0]) & (df[view_col] <= vr[1])]

        # Palette
        palette = sns.color_palette("coolwarm", as_cmap=True)

        st.subheader("🧾 Dataset Preview")
        st.dataframe(df.head())

        # Top Channels
        st.markdown("---")
        st.subheader("🏆 Top 10 Trending Channels")
        if 'channel_title' in df.columns:
            top = df['channel_title'].value_counts().head(10)
            fig, ax = plt.subplots()
            sns.barplot(x=top.values, y=top.index, ax=ax, palette="crest")
            st.pyplot(fig)

        # WordCloud
        st.markdown("---")
        st.subheader("☁️ Word Cloud of Video Titles")
        if 'title' in df.columns:
            title_text = " ".join(df['title'].dropna().astype(str))
            wc = WordCloud(width=800, height=400, background_color='black', colormap='Pastel1').generate(title_text)
            st.image(wc.to_array(), use_container_width=True)

        # Views Distribution
        st.markdown("---")
        st.subheader("📊 Views Distribution")
        if view_col:
            fig, ax = plt.subplots()
            sns.histplot(df[view_col], bins=30, kde=True, ax=ax, color='skyblue')
            st.pyplot(fig)

        # Correlation
        st.markdown("---")
        st.subheader("📌 Correlation Heatmap")
        nums = df.select_dtypes(include='number')
        if not nums.empty:
            fig, ax = plt.subplots()
            sns.heatmap(nums.corr(), annot=True, cmap="coolwarm", fmt=".2f", ax=ax)
            st.pyplot(fig)

        # Likes vs Dislikes
        like_col = next((c for c in ['like_count', 'likes'] if c in df.columns), None)
        dislike_col = next((c for c in ['dislike_count', 'dislikes'] if c in df.columns), None)
        if like_col and dislike_col:
            st.markdown("---")
            st.subheader("👍 Likes vs 👎 Dislikes")
            fig, ax = plt.subplots()
            sns.scatterplot(data=df, x=like_col, y=dislike_col, hue='channel_title', alpha=0.6, ax=ax)
            st.pyplot(fig)

        # Download CSV
        st.markdown("---")
        st.download_button("💾 Download Filtered CSV", df.to_csv(index=False), "filtered.csv", "text/csv")

# Interactive Video Explorer
with tabs[1]:
    st.title("🎥 Interactive Video Explorer")
    if uploaded_file and 'video_id' in df.columns:
        video_ids = df['video_id'].dropna().unique().tolist()
        selected_video = st.selectbox("Choose a video to preview", video_ids)
        if selected_video:
            st.video(f"https://www.youtube.com/watch?v={selected_video}")
    elif uploaded_file:
        st.warning("⚠️ No `video_id` column found for playback.")

# Pro Insights Tab
with tabs[2]:
    st.title("📊 Pro Insights")

    if uploaded_file:
        # Engagement Rate = (likes + comments) / views
        like_col = next((c for c in ['like_count', 'likes'] if c in df.columns), None)
        comment_col = next((c for c in ['comment_count', 'comments'] if c in df.columns), None)
        if like_col and comment_col and view_col:
            df['engagement_rate'] = ((df[like_col] + df[comment_col]) / df[view_col]).fillna(0)
            st.subheader("📈 Engagement Rate Histogram")
            fig, ax = plt.subplots()
            sns.histplot(df['engagement_rate'], bins=30, kde=True, color='violet', ax=ax)
            st.pyplot(fig)

        # Bubble Chart: Views vs Likes sized by comments
        if view_col and like_col and comment_col:
            st.subheader("🔵 Views vs Likes (Bubble Chart by Comments)")
            fig, ax = plt.subplots()
            bubble = ax.scatter(
                df[view_col], df[like_col], s=df[comment_col] / 10,
                c=df[comment_col], cmap='coolwarm', alpha=0.6, edgecolors='w'
            )
            ax.set_xlabel("Views")
            ax.set_ylabel("Likes")
            ax.set_title("Bubble Chart (Size = Comments)")
            st.pyplot(fig)

# About tab
with tabs[3]:
    st.title("🧑‍💻 Created by Soumya Singh")
    st.markdown("""
    This is a premium-level interactive dashboard for analyzing YouTube trending data.

    **Technologies Used:**
    - `Python` · `Streamlit` · `Pandas` · `Seaborn` · `WordCloud`
    - Lottie Animations
    - Embedded YouTube Video Preview
    - Pro-level visual insights like correlation, engagement rate, and bubble plots.

    Made with ❤️ by Soumya Singh
    """)
