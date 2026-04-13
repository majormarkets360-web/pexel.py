import streamlit as st
import requests
import json
import time
import random
from datetime import datetime
from moviepy import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips, CompositeAudioClip
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
video_duration = st.sidebar.slider("Video Duration (seconds)", 30, 120, 60)
video_quality = st.sidebar.selectbox("Video Quality", ["720p", "1080p"], index=1)

# ---------- Helper Functions ----------
@st.cache_data(ttl=3600)
def get_trending_topics():
    """Fetch trending topics from Google Trends, Hacker News, and Reddit."""
    topics = []
    
    # Progress bar for fetching
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Google Trends via pytrends (unofficial, but free)
    try:
        status_text.text("Fetching Google Trends...")
        pytrends = TrendReq(hl='en-US', tz=360)
        trending_searches = pytrends.trending_searches(pn='united_states')
        google_topics = trending_searches[0].tolist()[:5]
        topics.extend(google_topics)
        progress_bar.progress(33)
    except Exception as e:
        st.warning(f"Google Trends fetch failed: {e}")
    
    # Hacker News (free Firebase API)
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
    
    # Reddit (free, no auth for public data)
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
    
    return list(set(topics))  # remove duplicates

def search_pexels_videos(keyword, api_key, per_page=5):
    """Search Pexels for royalty-free video clips using direct API call."""
    if not api_key:
        st.warning("⚠️ Please enter your Pexels API key in the sidebar to search for videos.")
        return []
    
    # Pexels API expects the key directly, NOT with "Bearer " prefix
    headers = {
        'Authorization': api_key
    }
    
    # Use the videos endpoint with landscape orientation for better quality
    url = f'https://api.pexels.com/videos/search?query={keyword}&per_page={per_page}&orientation=landscape'
    
    try:
        with st.spinner(f"Searching Pexels for videos about '{keyword}'..."):
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                video_urls = []
                
                for video in data.get('videos', []):
                    # Get video files and find the best quality
                    video_files = video.get('video_files', [])
                    if video_files:
                        # Try to find landscape HD video
                        best_video = None
                        for vf in video_files:
                            if video_quality == "1080p" and vf.get('width', 0) >= 1920 and vf.get('height', 0) >= 1080:
                                best_video = vf
                                break
                            elif vf.get('width', 0) >= 1280 and vf.get('height', 0) >= 720:
                                best_video = vf
                        if not best_video:
                            best_video = video_files[0]
                        
                        if best_video and best_video.get('link'):
                            video_urls.append(best_video['link'])
                
                if video_urls:
                    st.success(f"✅ Found {len(video_urls)} videos for '{keyword}'")
                else:
                    st.warning(f"No videos found for '{keyword}'. Try a different topic.")
                
                return video_urls
            else:
                st.error(f"❌ Pexels API error {response.status_code}. Please check your API key.")
                return []
                
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
        return []
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return []

def generate_text(topic, hf_key):
    """Generate short engaging text/narration using Hugging Face API."""
    if not hf_key:
        # Fallback to simple template text
        return f"Discover the latest trends in {topic} and stay ahead of the curve! In this video, we explore everything you need to know about {topic}. From breaking news to expert insights, we've got you covered. Don't miss out on this exciting topic!"
    
    api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
    headers = {"Authorization": f"Bearer {hf_key}"}
    prompt = f"Write a {video_duration}-second engaging voiceover script for a video about '{topic}'. Keep it concise, exciting, and suitable for social media. Maximum 100 words."
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 150, "temperature": 0.7}}
    
    try:
        with st.spinner("Generating engaging script using AI..."):
            response = requests.post(api_url, headers=headers, json=payload)
            if response.status_code == 200:
                result = response.json()
                return result[0]['generated_text'].replace(prompt, "").strip()
            else:
                st.warning("AI generation failed. Using template text.")
                return f"Get ready to dive into {topic}! This trending topic is taking the world by storm. Watch now to learn all the exciting details and stay informed!"
    except Exception as e:
        st.warning(f"Text generation failed: {e}. Using template.")
        return f"Explore the fascinating world of {topic}! From amazing facts to important updates, this video has everything you need. Don't forget to like and subscribe!"

def download_video(url, filename):
    """Download video from URL."""
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except Exception as e:
        st.error(f"Failed to download video: {e}")
        return False
    return False

def create_video(topic, video_urls, text):
    """Compile video clips, add text overlays, and merge background music."""
    clips = []
    temp_files = []
    
    # Create progress bar for video creation
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Download and load video clips
    for i, url in enumerate(video_urls[:3]):  # use up to 3 clips
        status_text.text(f"Downloading video clip {i+1}/{min(3, len(video_urls))}...")
        filename = f"temp_clip_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        temp_files.append(filename)
        
        if download_video(url, filename):
            progress_bar.progress((i + 1) * 20)
            clip = VideoFileClip(filename)
            # Use shorter clip duration to fit more content
            clip_duration = min(20, clip.duration)
            clips.append(clip.subclipped(0, clip_duration))
    
    if not clips:
        st.error("No video clips were downloaded successfully.")
        return None
    
    status_text.text("Concatenating video clips...")
    progress_bar.progress(60)
    
    # Concatenate clips to reach desired duration
    final_clip = concatenate_videoclips(clips, method="compose")
    if final_clip.duration < video_duration:
        # loop the last clip to fill the remaining time
        last_clip = clips[-1]
        loops = int(video_duration / last_clip.duration) + 1
        final_clip = concatenate_videoclips([final_clip] + [last_clip] * loops)
    final_clip = final_clip.subclipped(0, video_duration)
    
    status_text.text("Adding text overlays...")
    progress_bar.progress(80)
    
    # Add text overlays (simple subtitles)
    try:
        # Split text into chunks for better display
        words = text.split()
        chunks = [' '.join(words[i:i+8]) for i in range(0, len(words), 8)]
        chunk_duration = video_duration / len(chunks)
        
        txt_clips = []
        for i, chunk in enumerate(chunks):
            txt_clip = TextClip(
                chunk, 
                font_size=30, 
                color='white', 
                font='Arial',
                stroke_color='black', 
                stroke_width=2,
                method='caption'
            )
            txt_clip = txt_clip.with_position(('center', 'bottom'))
            txt_clip = txt_clip.with_start(i * chunk_duration)
            txt_clip = txt_clip.with_duration(chunk_duration)
            txt_clips.append(txt_clip)
        
        final_clip = CompositeVideoClip([final_clip] + txt_clips)
    except Exception as e:
        st.warning(f"Text overlay failed: {e}. Continuing without text.")
    
    # Add background music (optional)
    bg_music_path = "background.mp3"
    if os.path.exists(bg_music_path):
        try:
            status_text.text("Adding background music...")
            audio_clip = AudioFileClip(bg_music_path)
            # Loop music if needed
            if audio_clip.duration < video_duration:
                audio_clip = audio_clip.loop(duration=video_duration)
            else:
                audio_clip = audio_clip.subclipped(0, video_duration)
            
            # Reduce music volume (background)
            audio_clip = audio_clip.with_volume_scaled(0.3)
            final_clip = final_clip.with_audio(audio_clip)
        except Exception as e:
            st.warning(f"Could not add background music: {e}")
    
    # Write output video
    status_text.text("Rendering final video...")
    progress_bar.progress(90)
    
    output_path = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    try:
        final_clip.write_videofile(output_path, fps=24, logger=None, verbose=False)
        progress_bar.progress(100)
        status_text.text("Video created successfully!")
    except Exception as e:
        st.error(f"Failed to render video: {e}")
        return None
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        status_text.empty()
        progress_bar.empty()
    
    return output_path

def post_to_twitter(video_path, caption, bearer_token):
    """Post video to X (Twitter) using free API tier."""
    if not bearer_token:
        st.error("Twitter Bearer Token not provided")
        return None
    
    try:
        client = tweepy.Client(bearer_token=bearer_token)
        # Note: media upload might require additional permissions
        # For simplicity, we'll post without media if it fails
        media = client.media_upload(video_path)
        response = client.create_tweet(text=caption[:280], media_ids=[media.media_id_string])
        return response
    except Exception as e:
        st.error(f"Twitter post failed: {e}")
        return None

def post_to_facebook(video_path, caption, access_token):
    """Post video to Facebook Page/Profile."""
    if not access_token:
        st.error("Facebook Access Token not provided")
        return None
    
    try:
        graph = facebook.GraphAPI(access_token=access_token)
        with open(video_path, 'rb') as video_file:
            response = graph.put_video(video=video_file, description=caption[:2000])
        return response
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
            with st.spinner("Fetching trending topics from multiple sources..."):
                topics = get_trending_topics()
                if topics:
                    st.session_state['topics'] = topics
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
    
    # Generate Video Button
    if st.button("🎬 Generate Video", type="primary", use_container_width=True):
        if not selected_topic:
            st.error("❌ Please select or enter a topic first.")
        elif not pexels_api_key:
            st.error("❌ Please enter your Pexels API key in the sidebar to search for videos.")
        else:
            # Step 1: Search for videos
            video_urls = search_pexels_videos(selected_topic, pexels_api_key)
            if not video_urls:
                st.stop()
            
            # Step 2: Generate narration text
            script = generate_text(selected_topic, hf_api_key)
            with st.expander("📝 Generated Script"):
                st.write(script)
            
            # Step 3: Create video
            st.info("⏳ This may take a few minutes depending on video length and quality...")
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
                
                # Social Media Posting Section
                st.markdown("---")
                st.markdown("### 📱 Share to Social Media")
                
                col_social1, col_social2 = st.columns(2)
                
                with col_social1:
                    if st.button("🐦 Post to Twitter", use_container_width=True):
                        if twitter_bearer_token:
                            caption = f"Check out this video about {selected_topic}! 🎬 #AIVideo #Trending"
                            result = post_to_twitter(video_file, caption, twitter_bearer_token)
                            if result:
                                st.success("✅ Posted to Twitter successfully!")
                        else:
                            st.warning("⚠️ Twitter Bearer Token not provided in sidebar.")
                
                with col_social2:
                    if st.button("📘 Post to Facebook", use_container_width=True):
                        if facebook_access_token:
                            caption = f"Check out this video about {selected_topic}! 🎬"
                            result = post_to_facebook(video_file, caption, facebook_access_token)
                            if result:
                                st.success("✅ Posted to Facebook successfully!")
                        else:
                            st.warning("⚠️ Facebook Access Token not provided in sidebar.")
                
                # Clean up old video files (optional)
                # os.remove(video_file)
            else:
                st.error("❌ Failed to create video. Please check your internet connection and try again.")

# ---------- Footer ----------
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    Made with ❤️ using Streamlit | Powered by Pexels API, Hugging Face, and MoviePy
    </div>
    """,
    unsafe_allow_html=True
)
