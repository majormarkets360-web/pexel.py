import streamlit as st
import requests
import json
import time
import random
from datetime import datetime
from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, TextClip, AudioFileClip, CompositeAudioClip
from pytrends.request import TrendReq
import os
from PIL import Image
from io import BytesIO
import base64

# ---------- Page Configuration ----------
st.set_page_config(page_title="AI Video Creator", page_icon="🎬", layout="wide")
st.title("🎬 AI Video Creator")
st.markdown("Generate engaging 1‑minute video clips from trending topics — for free.")

# ---------- Sidebar: Configuration ----------
st.sidebar.header("🔐 API Keys & Settings")
st.sidebar.info("All keys can be obtained for free from the respective platforms.")

# Pexels API (for video search)
pexels_api_key = st.sidebar.text_input(
    "Pexels API Key", 
    type="password",
    help="Get your free API key from https://www.pexels.com/api/"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📹 Video Settings")
video_duration = st.sidebar.slider("Video Duration (seconds)", 15, 60, 30)
video_quality = st.sidebar.selectbox("Video Quality", ["720p", "1080p"], index=0)

# ---------- Helper Functions ----------
@st.cache_data(ttl=3600)
def get_trending_topics():
    """Fetch trending topics from Google Trends, Hacker News, and Reddit."""
    topics = []
    
    # Google Trends
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        trending_searches = pytrends.trending_searches(pn='united_states')
        google_topics = trending_searches[0].tolist()[:3]
        topics.extend(google_topics)
    except Exception as e:
        st.warning(f"Google Trends: {e}")
    
    # Hacker News
    try:
        hn_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        top_stories = requests.get(hn_url).json()[:3]
        for story_id in top_stories:
            story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            story = requests.get(story_url).json()
            if story and 'title' in story:
                topics.append(story['title'])
    except Exception as e:
        st.warning(f"Hacker News: {e}")
    
    # Reddit
    try:
        reddit_url = "https://www.reddit.com/r/all/top.json?limit=3"
        reddit_data = requests.get(reddit_url, headers={'User-agent': 'StreamlitApp'}).json()
        for post in reddit_data['data']['children']:
            topics.append(post['data']['title'])
    except Exception as e:
        st.warning(f"Reddit: {e}")
    
    return list(set(topics))[:5]

def search_pexels_videos(keyword, api_key, per_page=3):
    """Search Pexels for royalty-free video clips."""
    if not api_key:
        return []
    
    api_key = api_key.strip()
    headers = {'Authorization': api_key}
    url = f'https://api.pexels.com/videos/search?query={keyword}&per_page={per_page}&orientation=landscape'
    
    try:
        with st.spinner(f"Searching for videos..."):
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                video_urls = []
                
                for video in data.get('videos', []):
                    video_files = video.get('video_files', [])
                    if video_files:
                        # Get the best quality video
                        best_video = video_files[0]
                        for vf in video_files:
                            if video_quality == "1080p" and vf.get('height', 0) >= 1080:
                                best_video = vf
                                break
                            elif vf.get('height', 0) >= 720:
                                best_video = vf
                        
                        if best_video and best_video.get('link'):
                            video_urls.append(best_video['link'])
                
                if video_urls:
                    st.success(f"✅ Found {len(video_urls)} videos")
                else:
                    st.warning(f"No videos found")
                
                return video_urls
            else:
                st.error(f"Pexels API error: {response.status_code}")
                return []
                
    except Exception as e:
        st.error(f"Error: {e}")
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
    except Exception as e:
        st.error(f"Download failed: {e}")
        return False
    return False

def create_simple_video(topic, video_urls):
    """Create video by simply concatenating clips without any complex operations."""
    
    temp_files = []
    output_path = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Download all video clips
        downloaded_paths = []
        for i, url in enumerate(video_urls):
            status_text.text(f"Downloading clip {i+1}/{len(video_urls)}...")
            filename = f"clip_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            temp_files.append(filename)
            
            if download_video(url, filename):
                downloaded_paths.append(filename)
                progress_bar.progress((i + 1) * 30)
        
        if not downloaded_paths:
            st.error("No videos downloaded")
            return None
        
        # Load video clips
        status_text.text("Loading video clips...")
        progress_bar.progress(50)
        
        clips = []
        for path in downloaded_paths:
            try:
                clip = VideoFileClip(path)
                # Take only first 10 seconds of each clip to keep video short
                clip_duration = min(10, clip.duration)
                clip = clip.subclip(0, clip_duration)
                clips.append(clip)
            except Exception as e:
                st.warning(f"Could not load clip: {e}")
        
        if not clips:
            st.error("No clips could be loaded")
            return None
        
        # Simple concatenation
        status_text.text("Concatenating clips...")
        progress_bar.progress(70)
        
        try:
            # Use the simplest concatenation method
            final_clip = concatenate_videoclips(clips)
        except:
            # If that fails, just use the first clip
            final_clip = clips[0]
        
        # Make sure video is not too long
        if final_clip.duration > video_duration:
            final_clip = final_clip.subclip(0, video_duration)
        
        # Write video file - using the simplest parameters
        status_text.text("Rendering final video...")
        progress_bar.progress(85)
        
        # Try to write video with minimal parameters
        try:
            final_clip.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac'
            )
        except Exception as e:
            st.error(f"Render error: {e}")
            # Try even simpler render
            try:
                final_clip.write_videofile(
                    output_path,
                    fps=24
                )
            except:
                # Last resort: just save the first clip
                clips[0].write_videofile(output_path, fps=24)
        
        # Clean up
        final_clip.close()
        for clip in clips:
            clip.close()
        
        progress_bar.progress(100)
        status_text.text("Video created!")
        
        # Clean temp files
        for f in temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
        else:
            return None
        
    except Exception as e:
        st.error(f"Video creation error: {str(e)}")
        return None
    finally:
        status_text.empty()
        progress_bar.empty()

# ---------- Main App UI ----------
st.markdown("### 🎯 Create Your Video")

# Simple topic input
selected_topic = st.text_input(
    "Enter a topic for your video",
    placeholder="e.g., Nature, Technology, Space, Animals, Sports...",
    help="Enter any topic you want to create a video about"
)

# Or use trending topics
st.markdown("---")
st.markdown("#### Or choose a trending topic:")

if st.button("🔥 Get Trending Topics", use_container_width=True):
    with st.spinner("Fetching trending topics..."):
        topics = get_trending_topics()
        if topics:
            st.session_state['trending_topics'] = topics

if 'trending_topics' in st.session_state:
    cols = st.columns(3)
    for i, topic in enumerate(st.session_state['trending_topics'][:3]):
        with cols[i]:
            if st.button(f"📌 {topic[:30]}", key=f"trend_{i}", use_container_width=True):
                selected_topic = topic
                st.session_state['selected_topic'] = topic
                st.rerun()

if 'selected_topic' in st.session_state:
    selected_topic = st.session_state['selected_topic']
    st.info(f"Selected topic: **{selected_topic}**")

st.markdown("---")

# Show API status
if pexels_api_key:
    st.success("✅ Pexels API key configured")
else:
    st.warning("⚠️ Please enter your Pexels API key in the sidebar")

st.markdown("---")

# Generate Video Button
if st.button("🎬 Generate Video", type="primary", use_container_width=True):
    if not selected_topic:
        st.error("❌ Please enter or select a topic first.")
    elif not pexels_api_key:
        st.error("❌ Please enter your Pexels API key in the sidebar.")
    else:
        st.info(f"Creating video about: **{selected_topic}**")
        
        # Search for videos
        video_urls = search_pexels_videos(selected_topic, pexels_api_key)
        
        if video_urls:
            st.success(f"Found {len(video_urls)} videos! Creating your video...")
            
            # Create video
            video_file = create_simple_video(selected_topic, video_urls)
            
            if video_file and os.path.exists(video_file):
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
                st.error("❌ Failed to create video. Please try a different topic.")
        else:
            st.error("No videos found for this topic. Please try a different topic.")

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
