import streamlit as st
import requests
import json
import time
import random
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import base64
from io import BytesIO

# ---------- Page Configuration ----------
st.set_page_config(page_title="AI Video Creator Pro", page_icon="🎬", layout="wide")
st.title("🎬 AI Video Creator Pro")
st.markdown("Generate 60-second viral videos with AI narration")

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

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎬 Video Settings")
video_duration = st.sidebar.slider("Target Duration (seconds)", 30, 90, 60)
video_quality = st.sidebar.selectbox("Quality", ["720p", "1080p"], index=0)
include_text_overlay = st.sidebar.checkbox("Add Text Overlay", value=True)

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

def create_html5_video_preview(video_urls, script, topic):
    """Create an HTML5 video preview using video URLs"""
    
    if not video_urls:
        return None
    
    # Create HTML with embedded videos
    video_html = f"""
    <div style="background: black; border-radius: 10px; padding: 20px;">
        <h3 style="color: white; text-align: center;">🎬 {topic.upper()}</h3>
    """
    
    for i, url in enumerate(video_urls[:3]):
        video_html += f"""
        <video width="100%" controls style="margin-bottom: 10px; border-radius: 5px;">
            <source src="{url}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
        """
    
    if script:
        video_html += f"""
        <div style="background: rgba(0,0,0,0.8); padding: 15px; border-radius: 5px; margin-top: 10px;">
            <p style="color: white; font-size: 16px; line-height: 1.5;">{script}</p>
        </div>
        """
    
    video_html += "</div>"
    
    return video_html

def create_text_overlay_image(text, width=1920, height=1080):
    """Create a text overlay image as base64"""
    try:
        # Create image
        img = Image.new('RGBA', (width, height), (0, 0, 0, 128))
        draw = ImageDraw.Draw(img)
        
        # Try to use a default font
        try:
            # For Streamlit Cloud - use default PIL font
            font = ImageFont.load_default()
            font_size = 20
        except:
            font = ImageFont.load_default()
            font_size = 20
        
        # Wrap text
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(' '.join(current_line)) > 40:
                lines.append(' '.join(current_line[:-1]))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        # Calculate position
        y_offset = height // 2 - (len(lines) * 30) // 2
        
        # Draw each line
        for line in lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                draw.text((x, y_offset), line, fill='white', font=font)
                y_offset += 40
            except:
                draw.text((width//2 - 100, y_offset), line, fill='white')
                y_offset += 40
        
        # Convert to base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        st.warning(f"Could not create text overlay: {e}")
        return None

def get_trending_topics():
    """Fetch trending topics without pytrends"""
    # Use static trending topics to avoid pytrends dependency
    topics = [
        "Artificial Intelligence",
        "Digital Marketing", 
        "Productivity Hacks",
        "Motivation",
        "Success Mindset",
        "Future Technology",
        "Social Media Growth",
        "Business Trends",
        "Climate Action",
        "Space Exploration",
        "Mental Health",
        "Fitness Motivation",
        "Crypto News",
        "Web3 Revolution",
        "Sustainable Living"
    ]
    
    # Try to get real trends using free API if available
    try:
        response = requests.get("https://trends.google.com/trends/api/dailytrends?hl=en-US&tz=-240&geo=US", timeout=5)
        if response.status_code == 200:
            # Parse response (skip first 5 characters)
            data = json.loads(response.text[5:])
            trends = data.get('default', {}).get('trendingSearches', [])[:5]
            if trends:
                trending = [trend.get('title', {}).get('query', '') for trend in trends if trend.get('title', {}).get('query')]
                if trending:
                    topics = trending + topics
    except:
        pass
    
    return list(set(topics))[:10]

def generate_video_script_html(topic, script):
    """Generate HTML representation of the video script"""
    html = f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 15px; 
                padding: 30px; 
                color: white;
                margin: 20px 0;">
        <h2 style="text-align: center; margin-bottom: 20px;">🎬 {topic.upper()}</h2>
        <div style="background: rgba(255,255,255,0.1); 
                    border-radius: 10px; 
                    padding: 20px;
                    font-size: 18px;
                    line-height: 1.6;">
            {script.replace(chr(10), '<br>')}
        </div>
        <p style="text-align: center; margin-top: 20px; font-size: 14px; opacity: 0.8;">
            ⏱️ Estimated duration: {video_duration} seconds
        </p>
    </div>
    """
    return html

# ---------- Main UI ----------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    
    st.markdown("### 🎯 Select Your Video Topic")
    
    tab1, tab2 = st.tabs(["🔥 Trending Topics", "✏️ Custom Topic"])
    
    with tab1:
        if st.button("🔄 Refresh Trends", use_container_width=True):
            with st.spinner("Fetching latest trends..."):
                topics = get_trending_topics()
                st.session_state['trending_topics'] = topics
                st.rerun()
        
        if 'trending_topics' in st.session_state:
            cols = st.columns(2)
            for i, topic in enumerate(st.session_state['trending_topics'][:6]):
                with cols[i % 2]:
                    if st.button(f"📌 {topic}", key=f"trend_{i}", use_container_width=True):
                        st.session_state['selected_topic'] = topic
                        st.rerun()
        else:
            # Initial load
            with st.spinner("Loading trending topics..."):
                st.session_state['trending_topics'] = get_trending_topics()
                st.rerun()
    
    with tab2:
        custom_topic = st.text_input("Enter your topic:", placeholder="e.g., Space Exploration, Digital Art, etc.")
        if custom_topic:
            if st.button("Use This Topic", use_container_width=True):
                st.session_state['selected_topic'] = custom_topic
                st.rerun()
    
    if 'selected_topic' in st.session_state:
        st.success(f"🎬 Selected Topic: **{st.session_state['selected_topic']}**")
        selected_topic = st.session_state['selected_topic']
    else:
        selected_topic = None
    
    st.markdown("---")
    
    if pexels_api_key:
        st.success("✅ Pexels API Ready")
    else:
        st.info("💡 Enter your Pexels API key to get started (free from pexels.com/api)")
    
    # Generate button
    if st.button("🎬 Generate Video Content", type="primary", use_container_width=True, disabled=not selected_topic or not pexels_api_key):
        if not selected_topic:
            st.error("Please select a topic first")
        elif not pexels_api_key:
            st.error("Please enter your Pexels API key in the sidebar")
        else:
            # Generate script
            with st.spinner("📝 Generating AI script..."):
                script = generate_ai_script(selected_topic, openai_api_key)
                
                # Display script in a nice format
                st.markdown("### 📝 Generated Script")
                st.markdown(generate_video_script_html(selected_topic, script), unsafe_allow_html=True)
                
                with st.expander("View Plain Text Script"):
                    st.text(script)
            
            # Search for videos
            with st.spinner("🎬 Searching for video clips..."):
                video_urls = search_pexels_videos(selected_topic, pexels_api_key)
            
            if not video_urls:
                st.warning(f"No videos found for '{selected_topic}'. Try a different topic or check your API key.")
                st.info("💡 Tip: Try more general topics like 'nature', 'technology', or 'business'")
            else:
                st.success(f"✅ Found {len(video_urls)} video clips!")
                
                # Display video preview
                st.markdown("### 🎥 Video Previews")
                for i, url in enumerate(video_urls):
                    with st.expander(f"Video Clip {i+1}"):
                        st.video(url)
                
                # Create text overlay if requested
                if include_text_overlay and script:
                    with st.spinner("🎨 Creating text overlay..."):
                        # Create multiple text overlays from script
                        sentences = script.split('.')[:5]
                        for i, sentence in enumerate(sentences):
                            if sentence.strip():
                                overlay_img = create_text_overlay_image(sentence.strip())
                                if overlay_img:
                                    st.markdown(f"**Text Overlay {i+1}:**")
                                    st.image(overlay_img, use_container_width=True)
                
                # Store results in session state
                st.session_state.video_ready = True
                st.session_state.video_urls = video_urls
                st.session_state.generated_script = script
                st.session_state.generated_topic = selected_topic
                
                st.markdown("---")
                st.success("✨ Content generation complete!")
                
                # Export options
                st.markdown("### 📋 Export Options")
                
                # Export script
                st.download_button(
                    label="📝 Download Script",
                    data=script,
                    file_name=f"{selected_topic.replace(' ', '_')}_script.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
                # Export video URLs
                video_urls_text = "\n".join(video_urls)
                st.download_button(
                    label="🎬 Download Video URLs",
                    data=video_urls_text,
                    file_name=f"{selected_topic.replace(' ', '_')}_video_urls.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
                # HTML preview
                with st.expander("Preview HTML5 Video Player"):
                    html_preview = create_html5_video_preview(video_urls, script, selected_topic)
                    if html_preview:
                        st.markdown(html_preview, unsafe_allow_html=True)
    
    # Display generated content if available
    if st.session_state.get('video_ready'):
        st.markdown("---")
        st.markdown("### 📦 Generated Content")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📝 Script**")
            st.info(st.session_state.get('generated_script', 'N/A')[:200] + "...")
        
        with col2:
            st.markdown("**🎬 Video Clips**")
            video_urls = st.session_state.get('video_urls', [])
            st.success(f"{len(video_urls)} clips available")
            for url in video_urls[:2]:
                st.markdown(f"- [Clip {video_urls.index(url)+1}]({url})")
        
        st.markdown("### 🎯 Next Steps")
        st.info("""
        **To create your final video:**
        1. Download the video clips using the URLs above
        2. Use a video editor like:
           - CapCut (Free)
           - DaVinci Resolve (Free)
           - Adobe Premiere (Paid)
        3. Combine clips with the generated script as voiceover
        4. Add text overlays for engagement
        """)

# ---------- Footer ----------
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    <p>🎬 AI Video Creator Pro | Generate scripts & find clips for viral videos</p>
    <p style='font-size: 12px;'>⚠️ Note: Final video editing requires external software</p>
    </div>
    """,
    unsafe_allow_html=True
)
