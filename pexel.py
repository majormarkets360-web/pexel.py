import streamlit as st
import requests
import json
import time
import random
import os
import subprocess
from datetime import datetime
from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, TextClip, AudioFileClip
from pytrends.request import TrendReq
import tweepy
from io import BytesIO

# ---------- Page Configuration ----------
st.set_page_config(page_title="AI Video Creator Pro", page_icon="🎬", layout="wide")
st.title("🎬 AI Video Creator Pro")
st.markdown("Generate 60-second viral videos with AI narration and auto-post to social media")

# ---------- Session State Initialization ----------
if 'video_ready' not in st.session_state:
    st.session_state.video_ready = False
if 'video_path' not in st.session_state:
    st.session_state.video_path = None

# ---------- Sidebar: Configuration ----------
st.sidebar.header("🔐 API Keys & Settings")

# Pexels API
pexels_api_key = st.sidebar.text_input(
    "Pexels API Key", 
    type="password",
    help="Get from https://www.pexels.com/api/"
)

# OpenAI API for text generation
openai_api_key = st.sidebar.text_input(
    "OpenAI API Key (Optional)", 
    type="password",
    help="Get from https://platform.openai.com/api-keys - enables better script generation"
)

# Social Media APIs
st.sidebar.markdown("### 📱 Social Media Auto-Posting")
twitter_bearer_token = st.sidebar.text_input("Twitter Bearer Token", type="password")
twitter_api_key = st.sidebar.text_input("Twitter API Key", type="password")
twitter_api_secret = st.sidebar.text_input("Twitter API Secret", type="password")
twitter_access_token = st.sidebar.text_input("Twitter Access Token", type="password")
twitter_access_secret = st.sidebar.text_input("Twitter Access Secret", type="password")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎬 Video Settings")
video_duration = st.sidebar.slider("Target Duration (seconds)", 30, 90, 60)
video_quality = st.sidebar.selectbox("Quality", ["720p", "1080p"], index=0)
include_text_overlay = st.sidebar.checkbox("Add Text Overlay", value=True)
auto_post = st.sidebar.checkbox("Auto-Post to Twitter", value=False)

# ---------- Core Functions ----------
def generate_ai_script(topic, api_key=None):
    """Generate engaging video script using AI or fallback templates"""
    
    if api_key and api_key.startswith('sk-'):
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            prompt = f"""Write a {video_duration}-second engaging voiceover script about '{topic}'. 
            The script should be exciting, fast-paced, and suitable for TikTok/Reels.
            Keep it under 150 words. Start with a hook, end with a call to action.
            Format as plain text without timestamps."""
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.7
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                script = data['choices'][0]['message']['content']
                return script.strip()
        except Exception as e:
            st.warning(f"OpenAI failed: {e}. Using fallback.")
    
    # Fallback templates - still engaging
    templates = [
        f"""🔥 {topic.upper()} IS TAKING OVER! Here's what you need to know.

Did you know that {topic} is changing the game right now? Industry experts are calling this the biggest shift in years.

From breakthrough innovations to must-know trends, we're breaking down everything in just 60 seconds.

Whether you're a beginner or pro, this is your chance to stay ahead of the curve.

Like and follow for more insights! 🚀""",

        f"""⚠️ STOP SCROLLING! {topic.title()} just dropped and it's MASSIVE.

Here's why everyone's talking about it right now...

{random.choice(['Experts', 'Creators', 'Leaders', 'Innovators'])} are calling this a game-changer. The numbers don't lie - this trend is exploding.

Want to know the secrets? Watch until the end.

Drop a comment if you're excited about this! 💯""",

        f"""✨ The FUTURE of {topic.upper()} is HERE.

In this video, we're revealing:
• The latest breakthroughs you missed
• Pro tips that actually work
• What's coming next

{random.choice(['Creators', 'Businesses', 'Everyone'])} needs to know this. The landscape is shifting fast.

Save this video and share with someone who needs to see it!

Subscribe for daily content! 🎯"""
    ]
    
    return random.choice(templates)

def search_pexels_videos(keyword, api_key, per_page=5):
    """Search for multiple high-quality video clips"""
    if not api_key:
        return []
    
    api_key = api_key.strip()
    headers = {'Authorization': api_key}
    
    # Search for multiple clips to get variety
    url = f'https://api.pexels.com/videos/search?query={keyword}&per_page={per_page}&orientation=landscape'
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            video_urls = []
            
            for video in data.get('videos', []):
                video_files = video.get('video_files', [])
                if video_files:
                    # Get best quality
                    best_video = video_files[0]
                    for vf in video_files:
                        if video_quality == "1080p" and vf.get('height', 0) >= 1080:
                            best_video = vf
                            break
                        elif vf.get('height', 0) >= 720:
                            best_video = vf
                    
                    if best_video and best_video.get('link'):
                        video_urls.append(best_video['link'])
            
            return video_urls[:4]  # Get up to 4 clips for 60 seconds
        else:
            return []
    except Exception as e:
        st.error(f"Pexels error: {e}")
        return []

def download_video(url, filename):
    """Download video with progress"""
    try:
        response = requests.get(url, stream=True, timeout=60)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=32768):
                    f.write(chunk)
            return True
    except:
        return False
    return False

def create_professional_video(topic, video_urls, script, output_path):
    """Create a 60-second video with text overlays and transitions"""
    
    temp_files = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Calculate clip durations
        num_clips = len(video_urls)
        clip_duration = video_duration / num_clips if num_clips > 0 else video_duration
        
        # Download and prepare clips
        clips = []
        for i, url in enumerate(video_urls):
            status_text.text(f"Downloading clip {i+1}/{num_clips}...")
            filename = f"temp_clip_{i}.mp4"
            temp_files.append(filename)
            
            if download_video(url, filename):
                progress_bar.progress(20 + (i * 15))
                clip = VideoFileClip(filename)
                # Trim to appropriate length
                duration = min(clip_duration, clip.duration)
                clip = clip.subclip(0, duration)
                clips.append(clip)
        
        if not clips:
            return None
        
        status_text.text("Concatenating clips...")
        progress_bar.progress(70)
        
        # Concatenate all clips
        final_video = concatenate_videoclips(clips, method="compose")
        
        # Trim to exact duration
        if final_video.duration > video_duration:
            final_video = final_video.subclip(0, video_duration)
        
        # Add text overlay if enabled
        if include_text_overlay and script:
            status_text.text("Adding text overlay...")
            progress_bar.progress(85)
            
            # Split script into chunks for subtitles
            words = script.split()
            chunk_size = max(5, len(words) // 8)  # ~8 text overlays
            chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
            chunk_duration = video_duration / len(chunks)
            
            text_clips = []
            for i, chunk in enumerate(chunks[:10]):  # Max 10 overlays
                try:
                    txt_clip = TextClip(
                        chunk,
                        fontsize=40,
                        color='white',
                        stroke_color='black',
                        stroke_width=2,
                        font='Arial-Bold',
                        method='caption',
                        size=(final_video.w * 0.9, None)
                    )
                    txt_clip = txt_clip.set_position(('center', 'bottom'))
                    txt_clip = txt_clip.set_start(i * chunk_duration)
                    txt_clip = txt_clip.set_duration(chunk_duration)
                    text_clips.append(txt_clip)
                except:
                    continue
            
            if text_clips:
                final_video = CompositeVideoClip([final_video] + text_clips)
        
        # Render final video
        status_text.text("Rendering final video...")
        progress_bar.progress(90)
        
        final_video.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            threads=4,
            preset='medium',
            logger=None,
            verbose=False
        )
        
        # Cleanup
        final_video.close()
        for clip in clips:
            clip.close()
        for txt in text_clips:
            txt.close()
        
        progress_bar.progress(100)
        status_text.text("Video ready!")
        
        return output_path
        
    except Exception as e:
        st.error(f"Video creation error: {e}")
        return None
    finally:
        # Clean temp files
        for f in temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
        status_text.empty()
        progress_bar.empty()

def post_to_twitter(video_path, caption, bearer_token=None, api_key=None, api_secret=None, access_token=None, access_secret=None):
    """Post video to Twitter/X with authentication"""
    
    caption = caption[:280]  # Twitter character limit
    
    # Try OAuth 1.0a first (required for media upload)
    if all([api_key, api_secret, access_token, access_secret]):
        try:
            auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
            client = tweepy.API(auth)
            
            # Upload media
            media = client.media_upload(video_path)
            
            # Post tweet
            client.update_status(status=caption, media_ids=[media.media_id])
            return True, "Posted with OAuth 1.0a"
        except Exception as e:
            error_msg = str(e)
    
    # Try OAuth 2.0 Bearer Token as fallback (may not support media)
    if bearer_token:
        try:
            client = tweepy.Client(bearer_token=bearer_token)
            # Note: Bearer token typically can't upload media
            response = client.create_tweet(text=caption)
            return True, "Posted text-only with Bearer token"
        except Exception as e:
            return False, f"Both auth methods failed: {e}"
    
    return False, "No valid Twitter credentials provided"

def get_trending_topics():
    """Fetch current trending topics"""
    topics = []
    
    # Google Trends
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        trending = pytrends.trending_searches(pn='united_states')
        topics.extend(trending[0].tolist()[:5])
    except:
        pass
    
    # Default topics if API fails
    if not topics:
        topics = [
            "Artificial Intelligence",
            "Digital Marketing",
            "Productivity Hacks",
            "Motivation",
            "Success Mindset",
            "Future Technology",
            "Social Media Growth",
            "Business Trends"
        ]
    
    return list(set(topics))[:8]

# ---------- Main UI ----------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    
    # Topic Selection
    st.markdown("### 🎯 Select Your Video Topic")
    
    tab1, tab2 = st.tabs(["🔥 Trending Topics", "✏️ Custom Topic"])
    
    with tab1:
        if st.button("Refresh Trends", use_container_width=True):
            with st.spinner("Fetching latest trends..."):
                topics = get_trending_topics()
                st.session_state['trending_topics'] = topics
        
        if 'trending_topics' in st.session_state:
            cols = st.columns(2)
            for i, topic in enumerate(st.session_state['trending_topics'][:6]):
                with cols[i % 2]:
                    if st.button(f"📌 {topic}", key=f"trend_{i}", use_container_width=True):
                        st.session_state['selected_topic'] = topic
                        st.rerun()
    
    with tab2:
        custom_topic = st.text_input("Enter your topic:", placeholder="e.g., Crypto Trading Tips")
        if custom_topic:
            st.session_state['selected_topic'] = custom_topic
    
    # Show selected topic
    if 'selected_topic' in st.session_state:
        st.info(f"🎬 Selected: **{st.session_state['selected_topic']}**")
        selected_topic = st.session_state['selected_topic']
    else:
        selected_topic = None
    
    st.markdown("---")
    
    # API Status
    if pexels_api_key:
        st.success("✅ Pexels API: Connected")
    else:
        st.warning("⚠️ Enter Pexels API Key")
    
    # Generate Button
    if st.button("🎬 Generate Professional Video", type="primary", use_container_width=True):
        if not selected_topic:
            st.error("Please select or enter a topic")
        elif not pexels_api_key:
            st.error("Please enter your Pexels API key")
        else:
            st.info(f"🎥 Creating 60-second video about: **{selected_topic}**")
            
            # Step 1: Generate script
            with st.spinner("📝 Generating AI script..."):
                script = generate_ai_script(selected_topic, openai_api_key)
                with st.expander("View Generated Script"):
                    st.write(script)
            
            # Step 2: Search for videos
            with st.spinner("🎬 Searching for video clips..."):
                video_urls = search_pexels_videos(selected_topic, pexels_api_key, per_page=4)
            
            if not video_urls:
                st.error(f"No videos found for '{selected_topic}'. Try a different topic.")
                st.stop()
            
            st.success(f"Found {len(video_urls)} video clips!")
            
            # Step 3: Create video
            output_file = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            
            with st.spinner("🎨 Creating professional video (this takes 2-3 minutes)..."):
                video_path = create_professional_video(selected_topic, video_urls, script, output_file)
            
            if video_path and os.path.exists(video_path):
                st.success("✅ Video created successfully!")
                st.session_state.video_ready = True
                st.session_state.video_path = video_path
                st.session_state.generated_script = script
                st.session_state.generated_topic = selected_topic
                
                # Display video
                st.markdown("### 🎥 Your Generated Video")
                with open(video_path, 'rb') as f:
                    video_bytes = f.read()
                st.video(video_bytes)
                
                # Download button
                with open(video_path, 'rb') as f:
                    st.download_button(
                        label="📥 Download Video (MP4)",
                        data=f,
                        file_name=f"{selected_topic.replace(' ', '_')}_video.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
            else:
                st.error("Failed to create video. Please try again.")
    
    # Auto-Post Section
    if st.session_state.get('video_ready') and st.session_state.get('video_path'):
        st.markdown("---")
        st.markdown("### 📱 Share to Social Media")
        
        col_post1, col_post2 = st.columns(2)
        
        with col_post1:
            caption = st.text_area(
                "Tweet Caption",
                value=f"🔥 Check out this video about {st.session_state.get('generated_topic', 'trending topic')}! 🎬\n\n#AIVideo #Trending",
                height=100
            )
        
        with col_post2:
            if st.button("🐦 Post to Twitter Now", type="primary", use_container_width=True):
                if any([twitter_bearer_token, twitter_api_key]):
                    with st.spinner("Posting to Twitter..."):
                        success, message = post_to_twitter(
                            st.session_state.video_path,
                            caption,
                            twitter_bearer_token,
                            twitter_api_key,
                            twitter_api_secret,
                            twitter_access_token,
                            twitter_access_secret
                        )
                        if success:
                            st.success(f"✅ {message}")
                        else:
                            st.error(f"❌ {message}")
                else:
                    st.warning("Please add Twitter API credentials in the sidebar")
        
        # Auto-post if enabled
        if auto_post and any([twitter_bearer_token, twitter_api_key]):
            with st.spinner("Auto-posting to Twitter..."):
                success, message = post_to_twitter(
                    st.session_state.video_path,
                    f"🔥 Check out this video about {st.session_state.get('generated_topic', 'trending topic')}! 🎬\n\n#AIVideo #Trending",
                    twitter_bearer_token,
                    twitter_api_key,
                    twitter_api_secret,
                    twitter_access_token,
                    twitter_access_secret
                )
                if success:
                    st.toast("✅ Auto-posted to Twitter!")
                else:
                    st.toast(f"Auto-post failed: {message}")

# ---------- Footer ----------
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
    <p>🎬 <strong>AI Video Creator Pro</strong> | Powered by Pexels API + OpenAI</p>
    <p style='font-size: 12px;'>Generates 60-second videos with AI scripts and auto-posting to social media</p>
    </div>
    """,
    unsafe_allow_html=True
)
