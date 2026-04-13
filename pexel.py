import streamlit as st
import requests
import json
import time
import random
from datetime import datetime
from moviepy import *
from pytrends.request import TrendReq
from pexels_api import API as PexelsAPI
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
pexels_api_key = st.sidebar.text_input("Pexels API Key", type="password")
twitter_bearer_token = st.sidebar.text_input("Twitter Bearer Token (for posting)", type="password")
facebook_access_token = st.sidebar.text_input("Facebook Access Token", type="password")

# ---------- Helper Functions ----------
@st.cache_data(ttl=3600)
def get_trending_topics():
    """Fetch trending topics from Google Trends, Hacker News, and Reddit."""
    topics = []
   
    # Google Trends via pytrends (unofficial, but free)
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        trending_searches = pytrends.trending_searches(pn='united_states')
        google_topics = trending_searches[0].tolist()[:5]
        topics.extend(google_topics)
    except Exception as e:
        st.warning(f"Google Trends fetch failed: {e}")
   
    # Hacker News (free Firebase API)
    try:
        hn_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        top_stories = requests.get(hn_url).json()[:5]
        for story_id in top_stories:
            story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            story = requests.get(story_url).json()
            if story and 'title' in story:
                topics.append(story['title'])
    except Exception as e:
        st.warning(f"Hacker News fetch failed: {e}")
   
    # Reddit (free, no auth for public data)
    try:
        reddit_url = "https://www.reddit.com/r/all/top.json?limit=5"
        reddit_data = requests.get(reddit_url, headers={'User-agent': 'StreamlitApp'}).json()
        for post in reddit_data['data']['children']:
            topics.append(post['data']['title'])
    except Exception as e:
        st.warning(f"Reddit fetch failed: {e}")
   
    return list(set(topics))  # remove duplicates

def search_pexels_videos(keyword, api_key, per_page=5):
    """Search Pexels for royalty-free video clips."""
    if not api_key:
        return []
    pexels = PexelsAPI(api_key)
    videos = pexels.search_videos(keyword, per_page=per_page)
    video_urls = []
    for video in videos.entries:
        # get medium quality video file (free tier allows download)
        video_urls.append(video.video_files[0]['link'])
    return video_urls

def generate_text(topic):
    """Generate short engaging text/narration using a free LLM API (Hugging Face)."""
    api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
    headers = {"Authorization": "Bearer hf_..."}  # replace with your free HF token
    prompt = f"Write a 30-second engaging voiceover script for a video about '{topic}'. Keep it concise and exciting."
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 150}}
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        return response.json()[0]['generated_text']
    except:
        return f"Discover the latest trends in {topic} and stay ahead of the curve!"

def create_video(topic, video_urls, text, bg_music_path="background.mp3"):
    """Compile video clips, add text overlays, and merge background music."""
    clips = []
    # Download and load video clips
    for i, url in enumerate(video_urls[:3]):  # use up to 3 clips
        resp = requests.get(url)
        with open(f"clip_{i}.mp4", "wb") as f:
            f.write(resp.content)
        clip = VideoFileClip(f"clip_{i}.mp4").subclip(0, min(20, VideoFileClip(f"clip_{i}.mp4").duration))
        clips.append(clip)
   
    # Concatenate clips to reach 60 seconds
    final_clip = concatenate_videoclips(clips, method="compose")
    if final_clip.duration < 60:
        # loop the last clip to fill the remaining time
        last_clip = clips[-1]
        loops = int(60 / last_clip.duration) + 1
        final_clip = concatenate_videoclips([final_clip] + [last_clip] * loops)
    final_clip = final_clip.subclip(0, 60)
   
    # Add text overlays (simple subtitles)
    txt_clip = TextClip(text, fontsize=24, color='white', font='Arial', stroke_color='black', stroke_width=2)
    txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(5).crossfadein(1).crossfadeout(1)
    final_clip = CompositeVideoClip([final_clip, txt_clip])
   
    # Add background music
    if os.path.exists(bg_music_path):
        audio_clip = AudioFileClip(bg_music_path).subclip(0, 60)
        final_audio = CompositeAudioClip([audio_clip])
        final_clip = final_clip.set_audio(final_audio)
   
    # Write output video
    output_path = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    final_clip.write_videofile(output_path, fps=24)
    return output_path

def post_to_twitter(video_path, caption, bearer_token):
    """Post video to X (Twitter) using free API tier."""
    client = tweepy.Client(bearer_token=bearer_token)
    media = client.media_upload(video_path)
    response = client.create_tweet(text=caption, media_ids=[media.media_id_string])
    return response

def post_to_facebook(video_path, caption, access_token):
    """Post video to Facebook Page/Profile."""
    graph = facebook.GraphAPI(access_token=access_token)
    with open(video_path, 'rb') as video_file:
        response = graph.put_video(video=video_file, description=caption)
    return response

# ---------- Main App UI ----------
topic_selection = st.radio("Choose topic source:", ("Trending Topics", "Enter Custom Topic"))

if topic_selection == "Trending Topics":
    with st.spinner("Fetching latest trends..."):
        topics = get_trending_topics()
    selected_topic = st.selectbox("Select a trending topic", topics)
else:
    selected_topic = st.text_input("Enter a custom topic")

if st.button("Generate Video"):
    if not selected_topic:
        st.error("Please select or enter a topic.")
    else:
        with st.spinner("Step 1/4: Fetching video clips..."):
            video_urls = search_pexels_videos(selected_topic, pexels_api_key)
            if not video_urls:
                st.error("No video clips found. Try a different topic.")
                st.stop()
       
        with st.spinner("Step 2/4: Generating text narration..."):
            script = generate_text(selected_topic)
       
        with st.spinner("Step 3/4: Assembling video (this may take a few minutes)..."):
            video_file = create_video(selected_topic, video_urls, script)
       
        st.success("Video created successfully!")
        st.video(video_file)
       
        # Social Media Posting
        st.subheader("📱 Share to Social Media")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Post to Twitter"):
                if twitter_bearer_token:
                    try:
                        post_to_twitter(video_file, f"Check out this video about {selected_topic}! #AIVideo", twitter_bearer_token)
                        st.success("Posted to Twitter!")
                    except Exception as e:
                        st.error(f"Twitter post failed: {e}")
                else:
                    st.warning("Twitter Bearer Token not provided.")
        with col2:
            if st.button("Post to Facebook"):
                if facebook_access_token:
                    try:
                        post_to_facebook(video_file, f"Check out this video about {selected_topic}!", facebook_access_token)
                        st.success("Posted to Facebook!")
                    except Exception as e:
                        st.error(f"Facebook post failed: {e}")
                else:
                    st.warning("Facebook Access Token not provided.")

