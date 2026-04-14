import streamlit as st
import requests
import random
from datetime import datetime
from moviepy.editor import VideoFileClip, concatenate_videoclips
from pytrends.request import TrendReq
import os

# ---------- Page Configuration ----------
st.set_page_config(page_title="AI Video Creator", page_icon="🎬", layout="wide")
st.title("🎬 AI Video Creator")
st.markdown("Generate short video clips from trending topics — for free.")

# ---------- Sidebar: Configuration ----------
st.sidebar.header("🔐 API Keys & Settings")

# Pexels API
pexels_api_key = st.sidebar.text_input(
    "Pexels API Key", 
    type="password",
    help="Get your free API key from https://www.pexels.com/api/"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📹 Video Settings")
video_duration = st.sidebar.slider("Video Duration (seconds)", 10, 30, 15)

# ---------- Helper Functions ----------
@st.cache_data(ttl=3600)
def get_trending_topics():
    """Fetch trending topics."""
    topics = []
    
    # Google Trends
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        trending_searches = pytrends.trending_searches(pn='united_states')
        google_topics = trending_searches[0].tolist()[:3]
        topics.extend(google_topics)
    except:
        pass
    
    # Add some default topics if API fails
    if not topics:
        topics = [
            "Artificial Intelligence",
            "Space Exploration", 
            "Climate Change",
            "Healthy Lifestyle",
            "Digital Marketing"
        ]
    
    return list(set(topics))[:5]

def search_pexels_videos(keyword, api_key):
    """Search Pexels for video clips."""
    if not api_key:
        return []
    
    api_key = api_key.strip()
    headers = {'Authorization': api_key}
    url = f'https://api.pexels.com/videos/search?query={keyword}&per_page=2&orientation=landscape'
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            video_urls = []
            
            for video in data.get('videos', []):
                video_files = video.get('video_files', [])
                if video_files:
                    # Get medium quality video
                    for vf in video_files:
                        if vf.get('height', 0) >= 720:
                            video_urls.append(vf.get('link'))
                            break
                    if not video_urls and video_files:
                        video_urls.append(video_files[0].get('link'))
            
            return video_urls[:2]  # Max 2 videos
        else:
            return []
    except:
        return []

def download_video(url, filename):
    """Download video from URL."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except:
        return False
    return False

def create_video(topic, video_urls):
    """Create simple concatenated video."""
    
    if not video_urls:
        return None
    
    temp_files = []
    output_path = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Download videos
        downloaded = []
        for i, url in enumerate(video_urls):
            status_text.text(f"Downloading video {i+1}/{len(video_urls)}...")
            filename = f"temp_{i}.mp4"
            temp_files.append(filename)
            
            if download_video(url, filename):
                downloaded.append(filename)
            progress_bar.progress((i + 1) * 40)
        
        if not downloaded:
            return None
        
        # Load clips
        status_text.text("Loading videos...")
        progress_bar.progress(60)
        
        clips = []
        for path in downloaded:
            try:
                clip = VideoFileClip(path)
                # Take only first few seconds
                duration = min(7, clip.duration)
                clip = clip.subclip(0, duration)
                clips.append(clip)
            except:
                continue
        
        if not clips:
            return None
        
        # Combine clips
        status_text.text("Combining videos...")
        progress_bar.progress(80)
        
        if len(clips) == 1:
            final_clip = clips[0]
        else:
            final_clip = concatenate_videoclips(clips)
        
        # Trim to desired length
        if final_clip.duration > video_duration:
            final_clip = final_clip.subclip(0, video_duration)
        
        # Save video
        status_text.text("Rendering video...")
        progress_bar.progress(90)
        
        final_clip.write_videofile(
            output_path,
            fps=24,
            verbose=False,
            logger=None
        )
        
        # Cleanup
        final_clip.close()
        for clip in clips:
            clip.close()
        
        for f in temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
        
        progress_bar.progress(100)
        status_text.text("Video ready!")
        
        return output_path if os.path.exists(output_path) else None
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None
    finally:
        status_text.empty()
        progress_bar.empty()

# ---------- Main App UI ----------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    
    # Topic Selection
    st.markdown("### 🎯 Select a Topic")
    
    # Option 1: Custom topic
    custom_topic = st.text_input("Or enter your own topic:", placeholder="e.g., Nature, Technology, Sports...")
    
    # Option 2: Trending topics
    st.markdown("#### 🔥 Trending Topics")
    
    if st.button("Get Trending Topics", use_container_width=True):
        with st.spinner("Fetching trends..."):
            topics = get_trending_topics()
            st.session_state['topics'] = topics
    
    if 'topics' in st.session_state:
        cols = st.columns(2)
        for i, topic in enumerate(st.session_state['topics'][:4]):
            with cols[i % 2]:
                if st.button(f"📌 {topic}", key=f"topic_{i}", use_container_width=True):
                    custom_topic = topic
                    st.rerun()
    
    st.markdown("---")
    
    # API Key Status
    if pexels_api_key:
        st.success("✅ Pexels API Key: Configured")
    else:
        st.warning("⚠️ Please add your Pexels API key in the sidebar")
    
    # Generate Button
    if st.button("🎬 Generate Short Video", type="primary", use_container_width=True):
        if not custom_topic:
            st.error("Please enter or select a topic")
        elif not pexels_api_key:
            st.error("Please add your Pexels API key in the sidebar")
        else:
            st.info(f"Creating video about: **{custom_topic}**")
            
            # Search for videos
            with st.spinner("Searching for videos..."):
                video_urls = search_pexels_videos(custom_topic, pexels_api_key)
            
            if video_urls:
                st.success(f"Found {len(video_urls)} videos!")
                
                # Create video
                video_file = create_video(custom_topic, video_urls)
                
                if video_file:
                    st.success("✅ Video created successfully!")
                    
                    # Display video
                    st.markdown("### 🎥 Your Video")
                    with open(video_file, 'rb') as f:
                        video_bytes = f.read()
                    st.video(video_bytes)
                    
                    # Download button
                    with open(video_file, 'rb') as f:
                        st.download_button(
                            label="📥 Download Video",
                            data=f,
                            file_name=video_file,
                            mime="video/mp4",
                            use_container_width=True
                        )
                else:
                    st.error("Failed to create video. Please try a different topic.")
            else:
                st.error(f"No videos found for '{custom_topic}'. Try a different topic.")

# ---------- Footer ----------
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    Made with ❤️ using Streamlit | Powered by Pexels API
    </div>
    """,
    unsafe_allow_html=True
)
