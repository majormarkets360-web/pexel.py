import streamlit as st
import requests
import json
import time
import random
import os
import subprocess
from datetime import datetime
from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip
from pytrends.request import TrendReq
import tweepy
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ---------- Page Configuration ----------
st.set_page_config(page_title="AI Video Creator Pro", page_icon="🎬", layout="wide")
st.title("🎬 AI Video Creator Pro")
st.markdown("Generate 60-second viral videos with AI narration and auto-post to social media")

# ---------- Session State ----------
if 'video_ready' not in st.session_state:
    st.session_state.video_ready = False
if 'video_path' not in st.session_state:
    st.session_state.video_path = None

# ---------- Sidebar ----------
st.sidebar.header("🔐 API Keys & Settings")

pexels_api_key = st.sidebar.text_input(
    "Pexels API Key", 
    type="password",
    help="Get from https://www.pexels.com/api/"
)

openai_api_key = st.sidebar.text_input(
    "OpenAI API Key (Optional)", 
    type="password",
    help="Better script generation"
)

st.sidebar.markdown("### 📱 Twitter Auto-Posting")
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
    """Generate engaging video script"""
    
    if api_key and api_key.startswith('sk-'):
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            prompt = f"""Write a {video_duration}-second engaging voiceover script about '{topic}'. 
            Keep it under 150 words. Make it exciting and suitable for short videos.
            Use short sentences. End with a call to action."""
            
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
                return data['choices'][0]['message']['content'].strip()
        except Exception as e:
            st.warning(f"OpenAI failed, using template")
    
    # Fallback templates
    templates = [
        f"""🔥 {topic.upper()} is changing everything!

Here's what you need to know right now.

Experts are calling this a game-changer.

The numbers are incredible.

Want to stay ahead?

Watch until the end!

Subscribe for more! 🚀""",

        f"""⚠️ STOP SCROLLING!

{topic.title()} is going VIRAL.

Here's why everyone's talking about it.

The truth might surprise you.

Share this with someone who needs to see it.

Drop a comment below! 💯""",

        f"""✨ The FUTURE of {topic.upper()} is HERE.

3 things you need to know:

1. It's growing faster than ever
2. The opportunities are massive
3. You can get started TODAY

Save this video.

Follow for more insights! 🎯"""
    ]
    
    return random.choice(templates)

def search_pexels_videos(keyword, api_key, per_page=5):
    """Search for video clips"""
    if not api_key:
        return []
    
    api_key = api_key.strip()
    headers = {'Authorization': api_key}
    url = f'https://api.pexels.com/videos/search?query={keyword}&per_page={per_page}&orientation=landscape'
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            video_urls = []
            
            for video in data.get('videos', []):
                video_files = video.get('video_files', [])
                if video_files:
                    best_video = video_files[0]
                    for vf in video_files:
                        if video_quality == "1080p" and vf.get('height', 0) >= 1080:
                            best_video = vf
                            break
                        elif vf.get('height', 0) >= 720:
                            best_video = vf
                    
                    if best_video and best_video.get('link'):
                        video_urls.append(best_video['link'])
            
            return video_urls[:4]
    except Exception as e:
        st.error(f"Pexels error: {e}")
    
    return []

def download_video(url, filename):
    """Download video file"""
    try:
        response = requests.get(url, stream=True, timeout=60)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=32768):
                    f.write(chunk)
            return True
    except:
        pass
    return False

def create_text_overlay_frame(text, size=(1920, 1080), duration=3):
    """Create a text overlay frame using PIL (no ImageMagick needed)"""
    try:
        # Create image with transparent background
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Try to use a default font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        except:
            try:
                font = ImageFont.truetype("Arial.ttf", 60)
            except:
                font = ImageFont.load_default()
        
        # Calculate text position (centered, near bottom)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (size[0] - text_width) // 2
        y = size[1] - text_height - 100
        
        # Draw text with black stroke
        for offset in [-2, -1, 0, 1, 2]:
            draw.text((x + offset, y + offset), text, fill='black', font=font)
        draw.text((x, y), text, fill='white', font=font)
        
        # Convert PIL to numpy array
        frame = np.array(img)
        
        # Convert to clip (will be implemented in main function)
        return frame
    except Exception as e:
        print(f"Text overlay error: {e}")
        return None

def create_professional_video(topic, video_urls, script, output_path):
    """Create video with concatenated clips"""
    
    temp_files = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
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
                try:
                    clip = VideoFileClip(filename)
                    duration = min(clip_duration, clip.duration)
                    clip = clip.subclip(0, duration)
                    clips.append(clip)
                except Exception as e:
                    st.warning(f"Could not load clip {i+1}: {e}")
        
        if not clips:
            return None
        
        status_text.text("Combining clips...")
        progress_bar.progress(70)
        
        # Concatenate all clips
        if len(clips) == 1:
            final_video = clips[0]
        else:
            final_video = concatenate_videoclips(clips, method="compose")
        
        # Trim to exact duration
        if final_video.duration > video_duration:
            final_video = final_video.subclip(0, video_duration)
        
        # Add text overlay using simpler method
        if include_text_overlay and script:
            status_text.text("Adding text overlay...")
            progress_bar.progress(85)
            
            # Split script into chunks
            words = script.split()
            chunk_size = max(8, len(words) // 6)
            chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
            chunks = chunks[:6]  # Max 6 overlays
            
            if chunks:
                from moviepy.editor import ImageClip
                
                # Get video dimensions
                video_width = final_video.w
                video_height = final_video.h
                
                text_clips = []
                chunk_duration = video_duration / len(chunks)
                
                for i, chunk in enumerate(chunks):
                    # Create text image
                    img = Image.new('RGBA', (video_width, video_height), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(img)
                    
                    # Use default font
                    try:
                        font_size = max(40, int(video_height * 0.05))
                        font = ImageFont.load_default()
                    except:
                        font = ImageFont.load_default()
                    
                    # Split long text into lines
                    words_in_chunk = chunk.split()
                    lines = []
                    current_line = []
                    for word in words_in_chunk:
                        current_line.append(word)
                        if len(' '.join(current_line)) > 30:
                            lines.append(' '.join(current_line[:-1]))
                            current_line = [word]
                    if current_line:
                        lines.append(' '.join(current_line))
                    
                    # Draw each line
                    y_offset = video_height - 150 - (len(lines) * 40)
                    for line in lines:
                        bbox = draw.textbbox((0, 0), line, font=font)
                        text_width = bbox[2] - bbox[0]
                        x = (video_width - text_width) // 2
                        draw.text((x, y_offset), line, fill='white', font=font)
                        y_offset += 50
                    
                    # Convert to clip
                    text_array = np.array(img)
                    text_clip = ImageClip(text_array, duration=chunk_duration)
                    text_clip = text_clip.set_position(('center', 'bottom'))
                    text_clip = text_clip.set_start(i * chunk_duration)
                    text_clips.append(text_clip)
                
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
        
        progress_bar.progress(100)
        status_text.text("Video ready!")
        
        return output_path if os.path.exists(output_path) else None
        
    except Exception as e:
        st.error(f"Video creation error: {e}")
        return None
    finally:
        for f in temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
        status_text.empty()
        progress_bar.empty()

def post_to_twitter(video_path, caption, bearer_token=None, api_key=None, api_secret=None, access_token=None, access_secret=None):
    """Post video to Twitter"""
    
    caption = caption[:280]
    
    # Try OAuth 1.0a first
    if all([api_key, api_secret, access_token, access_secret]):
        try:
            auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
            api = tweepy.API(auth)
            media = api.media_upload(video_path)
            api.update_status(status=caption, media_ids=[media.media_id])
            return True, "Posted with OAuth 1.0a"
        except Exception as e:
            error_msg = str(e)
    
    # Try Bearer token
    if bearer_token:
        try:
            client = tweepy.Client(bearer_token=bearer_token)
            client.create_tweet(text=caption)
            return True, "Posted text-only with Bearer token"
        except Exception as e:
            return False, f"Error: {e}"
    
    return False, "No valid Twitter credentials"

def get_trending_topics():
    """Fetch trending topics"""
    topics = []
    
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        trending = pytrends.trending_searches(pn='united_states')
        topics.extend(trending[0].tolist()[:5])
    except:
        pass
    
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
    
    st.markdown("### 🎯 Select Your Video Topic")
    
    tab1, tab2 = st.tabs(["🔥 Trending Topics", "✏️ Custom Topic"])
    
    with tab1:
        if st.button("Refresh Trends", use_container_width=True):
            with st.spinner("Fetching..."):
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
        custom_topic = st.text_input("Enter your topic:")
        if custom_topic:
            st.session_state['selected_topic'] = custom_topic
    
    if 'selected_topic' in st.session_state:
        st.info(f"🎬 Selected: **{st.session_state['selected_topic']}**")
        selected_topic = st.session_state['selected_topic']
    else:
        selected_topic = None
    
    st.markdown("---")
    
    if pexels_api_key:
        st.success("✅ Pexels API Ready")
    else:
        st.warning("⚠️ Enter Pexels API Key")
    
    if st.button("🎬 Generate 60-Second Video", type="primary", use_container_width=True):
        if not selected_topic:
            st.error("Please select a topic")
        elif not pexels_api_key:
            st.error("Please enter Pexels API key")
        else:
            # Generate script
            with st.spinner("📝 Generating script..."):
                script = generate_ai_script(selected_topic, openai_api_key)
                with st.expander("View Script"):
                    st.write(script)
            
            # Search for videos
            with st.spinner("🎬 Finding videos..."):
                video_urls = search_pexels_videos(selected_topic, pexels_api_key)
            
            if not video_urls:
                st.error(f"No videos found for '{selected_topic}'")
                st.stop()
            
            st.success(f"Found {len(video_urls)} clips!")
            
            # Create video
            output_file = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            
            with st.spinner("🎨 Creating video (2-3 minutes)..."):
                video_path = create_professional_video(selected_topic, video_urls, script, output_file)
            
            if video_path and os.path.exists(video_path):
                st.success("✅ Video ready!")
                st.session_state.video_ready = True
                st.session_state.video_path = video_path
                st.session_state.generated_script = script
                st.session_state.generated_topic = selected_topic
                
                st.markdown("### 🎥 Your Video")
                with open(video_path, 'rb') as f:
                    st.video(f.read())
                
                with open(video_path, 'rb') as f:
                    st.download_button(
                        label="📥 Download Video",
                        data=f,
                        file_name=f"{selected_topic.replace(' ', '_')}_video.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
            else:
                st.error("Failed to create video")
    
    # Auto-post section
    if st.session_state.get('video_ready') and st.session_state.get('video_path'):
        st.markdown("---")
        st.markdown("### 📱 Share to Social Media")
        
        caption = st.text_area(
            "Tweet Caption",
            value=f"🔥 Check out this video about {st.session_state.get('generated_topic', 'trending topic')}! 🎬\n\n#AIVideo #Trending",
            height=100
        )
        
        if st.button("🐦 Post to Twitter", type="primary", use_container_width=True):
            if any([twitter_bearer_token, twitter_api_key]):
                with st.spinner("Posting..."):
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
                st.warning("Add Twitter credentials in sidebar")
        
        if auto_post:
            post_to_twitter(
                st.session_state.video_path,
                f"🔥 Check out this video about {st.session_state.get('generated_topic', 'trending topic')}! 🎬\n\n#AIVideo #Trending",
                twitter_bearer_token,
                twitter_api_key,
                twitter_api_secret,
                twitter_access_token,
                twitter_access_secret
            )

# ---------- Footer ----------
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    <p>🎬 AI Video Creator Pro | 60-Second Videos | Auto-Post to Twitter</p>
    </div>
    """,
    unsafe_allow_html=True
)
