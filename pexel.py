import streamlit as st
import requests
import json
import time
import random
from datetime import datetime
from moviepy import VideoFileClip, concatenate_videoclips
from pytrends.request import TrendReq
import tweepy
import facebook
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

# Social Media APIs
twitter_bearer_token = st.sidebar.text_input("Twitter Bearer Token (for posting)", type="password")
facebook_access_token = st.sidebar.text_input("Facebook Access Token", type="password")

# Hugging Face API (for text generation)
hf_api_key = st.sidebar.text_input(
    "Hugging Face API Key", 
    type="password",
    help="Get free API key from https://huggingface.co/settings/tokens"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📹 Video Settings")
video_duration = st.sidebar.slider("Video Duration (seconds)", 30, 90, 60)
video_quality = st.sidebar.selectbox("Video Quality", ["720p", "1080p"], index=0)

# ---------- Helper Functions ----------
@st.cache_data(ttl=3600)
def get_trending_topics():
    """Fetch trending topics from Google Trends, Hacker News, and Reddit."""
    topics = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Google Trends via pytrends
    try:
        status_text.text("Fetching Google Trends...")
        pytrends = TrendReq(hl='en-US', tz=360)
        trending_searches = pytrends.trending_searches(pn='united_states')
        google_topics = trending_searches[0].tolist()[:5]
        topics.extend(google_topics)
        progress_bar.progress(33)
    except Exception as e:
        st.warning(f"Google Trends fetch failed: {e}")
    
    # Hacker News
    try:
        status_text.text("Fetching Hacker News...")
        hn_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        top_stories = requests.get(hn_url).json()[:5]
        for story_id in top_stories:
            story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            story = requests.get(story_url).json()
            if story and 'title' in story:
                topics.append(story['title'])
        progress_bar.progress(66)
    except Exception as e:
        st.warning(f"Hacker News fetch failed: {e}")
    
    # Reddit
    try:
        status_text.text("Fetching Reddit trends...")
        reddit_url = "https://www.reddit.com/r/all/top.json?limit=5"
        reddit_data = requests.get(reddit_url, headers={'User-agent': 'StreamlitApp'}).json()
        for post in reddit_data['data']['children']:
            topics.append(post['data']['title'])
        progress_bar.progress(100)
    except Exception as e:
        st.warning(f"Reddit fetch failed: {e}")
    
    status_text.empty()
    progress_bar.empty()
    
    return list(set(topics))[:10]  # Return unique topics, max 10

def search_pexels_videos(keyword, api_key, per_page=5):
    """Search Pexels for royalty-free video clips."""
    if not api_key:
        st.warning("⚠️ Please enter your Pexels API key in the sidebar.")
        return []
    
    api_key = api_key.strip()
    headers = {'Authorization': api_key}
    url = f'https://api.pexels.com/videos/search?query={keyword}&per_page={per_page}&orientation=landscape'
    
    try:
        with st.spinner(f"Searching Pexels for videos about '{keyword}'..."):
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
                    st.success(f"✅ Found {len(video_urls)} videos for '{keyword}'")
                else:
                    st.warning(f"No videos found for '{keyword}'. Try a different topic.")
                
                return video_urls
            elif response.status_code == 401:
                st.error("❌ Invalid Pexels API key. Please check your key.")
                return []
            else:
                st.error(f"❌ Pexels API error {response.status_code}")
                return []
                
    except Exception as e:
        st.error(f"Error: {e}")
        return []

def generate_text(topic, hf_key):
    """Generate short engaging text/narration."""
    # Simple template text (avoids API issues)
    templates = [
        f"Discover the latest trends in {topic}! In this video, we explore everything you need to know about {topic}. From breaking news to expert insights, we've got you covered. Don't miss out on this exciting topic!",
        f"Get ready to dive into {topic}! This trending topic is taking the world by storm. Watch now to learn all the exciting details and stay informed!",
        f"Explore the fascinating world of {topic}! From amazing facts to important updates, this video has everything you need. Don't forget to like and subscribe!"
    ]
    return random.choice(templates)

def download_video(url, filename):
    """Download video from URL."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
            return True
    except Exception as e:
        st.error(f"Failed to download video: {e}")
        return False
    return False

def create_video(topic, video_urls, text):
    """Create video by concatenating clips using MoviePy only."""
    
    temp_files = []
    output_path = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Download all video clips
        downloaded_paths = []
        for i, url in enumerate(video_urls[:3]):  # Max 3 clips
            status_text.text(f"Downloading clip {i+1}/{min(3, len(video_urls))}...")
            filename = f"temp_clip_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            temp_files.append(filename)
            
            if download_video(url, filename):
                downloaded_paths.append(filename)
                progress_bar.progress((i + 1) * 25)
        
        if not downloaded_paths:
            st.error("No videos could be downloaded")
            return None
        
        # Load and trim video clips
        status_text.text("Loading video clips...")
        progress_bar.progress(50)
        
        clips = []
        for path in downloaded_paths:
            try:
                clip = VideoFileClip(path)
                # Take first 15-20 seconds of each clip
                clip_duration = min(20, clip.duration)
                clip = clip.subclipped(0, clip_duration)
                clips.append(clip)
            except Exception as e:
                st.warning(f"Could not load clip: {e}")
        
        if not clips:
            st.error("No clips could be loaded")
            return None
        
        # Concatenate clips
        status_text.text("Concatenating video clips...")
        progress_bar.progress(70)
        
        try:
            final_clip = concatenate_videoclips(clips, method="compose")
        except Exception as e:
            st.error(f"Failed to concatenate: {e}")
            # Try alternative method
            final_clip = concatenate_videoclips(clips, method="chain")
        
        # Trim to desired duration
        if final_clip.duration > video_duration:
            final_clip = final_clip.subclipped(0, video_duration)
        
        # Render final video
        status_text.text("Rendering final video...")
        progress_bar.progress(85)
        
        final_clip.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            logger=None
        )
        
        # Clean up
        final_clip.close()
        for clip in clips:
            clip.close()
        
        progress_bar.progress(100)
        status_text.text("Video created successfully!")
        
        # Clean up temp files
        for f in temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
        
        return output_path
        
    except Exception as e:
        st.error(f"Video creation error: {str(e)}")
        return None
    finally:
        status_text.empty()
        progress_bar.empty()

def post_to_twitter(video_path, caption, bearer_token):
    """Post video to X (Twitter)."""
    if not bearer_token:
        return None
    
    try:
        client = tweepy.Client(bearer_token=bearer_token)
        # Twitter API v2 media upload requires additional setup
        # For now, just return success message
        st.info("Twitter posting requires additional API setup. Video saved locally.")
        return None
    except Exception as e:
        st.error(f"Twitter post failed: {e}")
        return None

def post_to_facebook(video_path, caption, access_token):
    """Post video to Facebook."""
    if not access_token:
        return None
    
    try:
        st.info("Facebook posting requires additional API setup. Video saved locally.")
        return None
    except Exception as e:
        st.error(f"Facebook post failed: {e}")
        return None

# ---------- Main App UI ----------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("### 🎯 Topic Selection")
    
    topic_selection = st.radio(
        "Choose topic source:", 
        ("🔥 Trending Topics", "✏️ Enter Custom Topic"),
        horizontal=True
    )
    
    if topic_selection == "🔥 Trending Topics":
        if st.button("🔄 Fetch Latest Trends", use_container_width=True):
            with st.spinner("Fetching trending topics..."):
                topics = get_trending_topics()
                if topics:
                    st.session_state['topics'] = topics
                    st.success(f"Found {len(topics)} trending topics!")
                else:
                    st.error("Could not fetch topics. Please enter a custom topic.")
        
        if 'topics' in st.session_state and st.session_state['topics']:
            selected_topic = st.selectbox("Select a trending topic", st.session_state['topics'])
        else:
            selected_topic = None
            st.info("Click the button above to fetch trending topics.")
    else:
        selected_topic = st.text_input("Enter a custom topic", placeholder="e.g., Artificial Intelligence, Climate Change, Space Exploration...")
    
    st.markdown("---")
    
    # Show API key status
    if pexels_api_key:
        st.success("✅ Pexels API key provided")
    else:
        st.warning("⚠️ Please enter your Pexels API key in the sidebar")
    
    # Generate Video Button
    if st.button("🎬 Generate Video", type="primary", use_container_width=True):
        if not selected_topic:
            st.error("❌ Please select or enter a topic first.")
        elif not pexels_api_key:
            st.error("❌ Please enter your Pexels API key in the sidebar.")
        else:
            # Step 1: Search for videos
            st.info("📹 Step 1/3: Searching for videos...")
            video_urls = search_pexels_videos(selected_topic, pexels_api_key)
            if not video_urls:
                st.stop()
            
            # Step 2: Generate narration text
            st.info("📝 Step 2/3: Generating narration...")
            script = generate_text(selected_topic, hf_api_key)
            with st.expander("📝 View Script"):
                st.write(script)
            
            # Step 3: Create video
            st.info("🎬 Step 3/3: Creating video (this may take 2-3 minutes)...")
            video_file = create_video(selected_topic, video_urls, script)
            
            if video_file and os.path.exists(video_file):
                st.success("✅ Video created successfully!")
                
                # Display video
                st.markdown("### 🎥 Your Generated Video")
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
                st.error("❌ Failed to create video. Please try again with a different topic.")

# ---------- Footer ----------
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    Made with ❤️ using Streamlit | Powered by Pexels API and MoviePy
    </div>
    """,
    unsafe_allow_html=True
)
