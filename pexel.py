
    from src.trend_finder      import get_trending_topics
    from src.script_generator  import generate_script
    from src.video_builder     import build_video
    from src.scheduler         import AutoPostScheduler
    from src.social_media      import post_to_platforms
    return get_trending_topics, generate_script, build_video, AutoPostScheduler, post_to_platforms

# â”€â”€ Sidebar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/video-playlist.png", width=64)
    st.title("AutoVid Poster")
    st.caption("AI-powered video creation & auto-posting")
    st.divider()

    page = st.radio(
        "Navigate",
        ["ðŸ  Dashboard", "ðŸŽ¬ Generate Video", "ðŸ¤– Auto-Post Settings",
         "ðŸ”‘ API Keys", "ðŸ“‹ Post History"],
        label_visibility="collapsed",
    )

    st.divider()
    # Quick status
    st.markdown("**System Status**")
    apis = st.session_state.api_keys
    checks = {
        "Anthropic":   bool(apis["anthropic"]),
        "ElevenLabs":  bool(apis["elevenlabs"]),
        "Pexels":      bool(apis["pexels"]),
        "YouTube":     bool(apis["youtube_creds"]),
        "Instagram":   bool(apis["instagram_user"]),
        "TikTok":      bool(apis["tiktok_session"]),
        "Twitter/X":   bool(apis["twitter_key"]),
    }
    for name, ok in checks.items():
        icon = "ðŸŸ¢" if ok else "ðŸ”´"
        st.caption(f"{icon} {name}")

    st.divider()
    scheduler_label = "â¹ Stop Scheduler" if st.session_state.scheduler_running else "â–¶ï¸ Start Scheduler"
    if st.button(scheduler_label, use_container_width=True):
        st.session_state.scheduler_running = not st.session_state.scheduler_running
        st.rerun()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PAGE: DASHBOARD
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
if page == "ðŸ  Dashboard":
    st.markdown("""
    <div class="main-header">
        <h1>ðŸŽ¬ AutoVid Poster</h1>
        <p>Generate 60-second AI videos and autonomously post them across all platforms</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    history = st.session_state.post_history
    with col1:
        st.metric("Total Posts", len(history))
    with col2:
        yt = sum(1 for p in history if "YouTube" in p.get("platforms", []))
        st.metric("YouTube Uploads", yt)
    with col3:
        ig = sum(1 for p in history if "Instagram" in p.get("platforms", []))
        st.metric("Instagram Posts", ig)
    with col4:
        tt = sum(1 for p in history if "TikTok" in p.get("platforms", []))
        st.metric("TikTok Videos", tt)

    st.divider()
    col_a, col_b = st.columns([2, 1])

    with col_a:
        st.subheader("ðŸ“ˆ Trending Topics Right Now")
        if st.button("ðŸ”„ Refresh Trends"):
            st.cache_resource.clear()
        try:
            get_trending_topics, *_ = load_modules()
            trends = get_trending_topics(10)
            for i, t in enumerate(trends, 1):
                col_num, col_topic, col_btn = st.columns([0.5, 3, 1.5])
                col_num.write(f"**#{i}**")
                col_topic.write(t)
                if col_btn.button("Generate â†’", key=f"trend_{i}"):
                    st.session_state.generated_topic = t
                    st.info(f"Topic set to **{t}** â€” go to ðŸŽ¬ Generate Video to create!")
        except Exception as e:
            st.warning(f"Could not load trends: {e}")
            st.info("Check your API keys in the ðŸ”‘ API Keys page.")

    with col_b:
        st.subheader("âš™ï¸ Scheduler Status")
        if st.session_state.scheduler_running:
            st.success("ðŸŸ¢ Auto-Poster RUNNING")
            settings = st.session_state.schedule_settings
            st.write(f"**Interval:** Every {settings['interval_hours']}h")
            st.write(f"**Platforms:** {', '.join(settings['platforms'])}")
            st.write(f"**Posts/day:** {settings['max_posts_per_day']}")
        else:
            st.warning("ðŸ”´ Auto-Poster STOPPED")
            st.write("Start the scheduler from the sidebar or Auto-Post Settings page.")

        st.divider()
        if history:
            st.subheader("ðŸ•’ Last Post")
            last = history[-1]
            st.write(f"**Topic:** {last.get('topic','â€”')}")
            st.write(f"**Time:** {last.get('timestamp','â€”')}")
            st.write(f"**Platforms:** {', '.join(last.get('platforms',[]))}")

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PAGE: GENERATE VIDEO
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
elif page == "ðŸŽ¬ Generate Video":
    st.title("ðŸŽ¬ Generate a 60-Second Video")

    tab1, tab2 = st.tabs(["âœï¸ Custom Topic", "ðŸ“ˆ Pick from Trending"])

    with tab1:
        topic_input = st.text_input(
            "Enter your video topic",
            value=st.session_state.generated_topic,
            placeholder="e.g. '5 surprising facts about black holes'",
        )

    with tab2:
        try:
            get_trending_topics, *_ = load_modules()
            trends = get_trending_topics(10)
            selected_trend = st.selectbox("Choose a trending topic", trends)
            if st.button("Use this topic"):
                topic_input = selected_trend
                st.session_state.generated_topic = selected_trend
                st.success(f"Topic set: **{selected_trend}**")
        except Exception as e:
            st.error(f"Could not load trends: {e}")
            selected_trend = ""

    st.divider()
    col_settings, col_preview = st.columns([1, 2])

    with col_settings:
        st.subheader("âš™ï¸ Video Settings")
        voice_option = st.selectbox(
            "Voice style",
            ["Professional Male", "Professional Female", "Casual Male", "Casual Female", "Energetic"],
        )
        video_style = st.selectbox(
            "Visual style",
            ["Documentary", "Cinematic", "Fast-paced", "Calm & Educational"],
        )
        add_captions = st.toggle("Burn-in captions", value=True)
        add_music    = st.toggle("Background music", value=False)
        post_after   = st.toggle("Auto-post after generation", value=False)

        if post_after:
            platforms = st.multiselect(
                "Post to",
                ["YouTube", "TikTok", "Instagram", "Twitter/X"],
                default=["YouTube", "TikTok"],
            )

    with col_preview:
        st.subheader("ðŸ“½ï¸ Video Preview")

        final_topic = topic_input or st.session_state.generated_topic

        if st.button("ðŸš€ Generate 60-Second Video", type="primary", use_container_width=True):
            if not final_topic:
                st.error("Please enter or select a topic first.")
            elif not st.session_state.api_keys["anthropic"]:
                st.error("Anthropic API key required. Go to ðŸ”‘ API Keys.")
            elif not st.session_state.api_keys["pexels"]:
                st.error("Pexels API key required. Go to ðŸ”‘ API Keys.")
            else:
                progress_bar = st.progress(0, text="Startingâ€¦")
                status       = st.empty()

                try:
                    get_trending_topics, generate_script, build_video, _, post_to_platforms = load_modules()

                    status.info("âœï¸ Generating AI scriptâ€¦")
                    progress_bar.progress(15, text="Writing scriptâ€¦")
                    script = generate_script(
                        topic=final_topic,
                        api_key=st.session_state.api_keys["anthropic"],
                        duration_seconds=60,
                    )

                    status.info("ðŸŽ™ï¸ Creating voiceoverâ€¦")
                    progress_bar.progress(35, text="Generating voiceoverâ€¦")

                    status.info("ðŸŽ¥ Downloading stock footage from Pexelsâ€¦")
                    progress_bar.progress(55, text="Fetching footageâ€¦")

                    status.info("ðŸŽžï¸ Assembling 60-second videoâ€¦")
                    progress_bar.progress(75, text="Assembling videoâ€¦")

                    output_path = build_video(
                        topic=final_topic,
                        script=script,
                        pexels_api_key=st.session_state.api_keys["pexels"],
                        elevenlabs_api_key=st.session_state.api_keys["elevenlabs"],
                        duration=60,
                        add_captions=add_captions,
                        add_music=add_music,
                        style=video_style,
                    )

                    progress_bar.progress(95, text="Finalizingâ€¦")
                    st.session_state.generated_video_path = output_path
                    st.session_state.generated_topic      = final_topic
                    progress_bar.progress(100, text="Done!")
                    status.success("âœ… Video generated successfully!")

                    if post_after:
                        status.info("ðŸ“¤ Posting to platformsâ€¦")
                        results = post_to_platforms(
                            video_path=output_path,
                            title=final_topic,
                            description=f"AI-generated video about: {final_topic}",
                            platforms=platforms,
                            api_keys=st.session_state.api_keys,
                        )
                        st.session_state.post_history.append({
                            "topic":     final_topic,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "platforms": platforms,
                            "results":   results,
                        })
                        status.success("âœ… Posted to all platforms!")

                except Exception as e:
                    status.error(f"Error: {e}")
                    st.exception(e)

        if st.session_state.generated_video_path and Path(st.session_state.generated_video_path).exists():
            st.video(st.session_state.generated_video_path)
            with open(st.session_state.generated_video_path, "rb") as f:
                st.download_button("â¬‡ï¸ Download Video", f, file_name="autovid_output.mp4", mime="video/mp4")

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PAGE: AUTO-POST SETTINGS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
elif page == "ðŸ¤– Auto-Post Settings":
    st.title("ðŸ¤– Autonomous Posting Settings")
    settings = st.session_state.schedule_settings

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("ðŸ“… Schedule")
        settings["interval_hours"] = st.slider(
            "Post every N hours", 1, 24, settings["interval_hours"]
        )
        settings["max_posts_per_day"] = st.slider(
            "Max posts per day", 1, 24, settings["max_posts_per_day"]
        )

        st.subheader("ðŸ“¡ Platforms")
        settings["platforms"] = st.multiselect(
            "Post to these platforms",
            ["YouTube", "TikTok", "Instagram", "Twitter/X"],
            default=settings["platforms"],
        )

    with col2:
        st.subheader("ðŸ“ Topic Source")
        settings["use_trending"] = st.toggle(
            "Use trending topics automatically", value=settings["use_trending"]
        )

        custom_topics_raw = st.text_area(
            "Custom topic list (one per line â€” used when trending is off, or rotated in)",
            value="\n".join(settings.get("custom_topics", [])),
            height=150,
            placeholder="5 ways to save money\nBest travel destinations 2025\nAI breakthroughs this week",
        )
        settings["custom_topics"] = [t.strip() for t in custom_topics_raw.splitlines() if t.strip()]

        st.subheader("ðŸŽ¬ Video Defaults")
        settings["add_captions"] = st.toggle("Always burn-in captions", value=settings["add_captions"])
        settings["add_music"]    = st.toggle("Always add background music", value=settings["add_music"])

    st.session_state.schedule_settings = settings
    st.divider()

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("â–¶ï¸ Start Auto-Poster", type="primary", use_container_width=True,
                     disabled=st.session_state.scheduler_running):
            if not settings["platforms"]:
                st.error("Select at least one platform.")
            elif not st.session_state.api_keys["anthropic"]:
                st.error("Anthropic API key is required.")
            else:
                st.session_state.scheduler_running = True
                _, _, build_video, AutoPostScheduler, post_to_platforms = load_modules()
                get_trending_topics, generate_script, *_ = load_modules()

                def run_scheduler():
                    scheduler = AutoPostScheduler(
                        generate_script_fn=generate_script,
                        build_video_fn=build_video,
                        post_fn=post_to_platforms,
                        settings=st.session_state.schedule_settings,
                        api_keys=st.session_state.api_keys,
                        history=st.session_state.post_history,
                    )
                    scheduler.run()

                t = threading.Thread(target=run_scheduler, daemon=True)
                t.start()
                st.session_state.scheduler_thread = t
                st.success("âœ… Auto-poster started!")
                st.rerun()

    with col_b:
        if st.button("â¹ Stop Auto-Poster", use_container_width=True,
                     disabled=not st.session_state.scheduler_running):
            st.session_state.scheduler_running = False
            st.warning("Scheduler stopping after current taskâ€¦")
            st.rerun()

    with col_c:
        if st.button("ðŸ” Generate & Post Now", use_container_width=True):
            st.info("Navigating to Generate Video page â€” click **ðŸš€ Generate** there.")

    if st.session_state.scheduler_running:
        st.success(f"ðŸŸ¢ Scheduler ACTIVE â€” posting every {settings['interval_hours']} hours "
                   f"to: {', '.join(settings['platforms'])}")

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PAGE: API KEYS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
elif page == "ðŸ”‘ API Keys":
    st.title("ðŸ”‘ API Configuration")
    st.info("Keys are stored in session state only. For persistence, add them to a `.env` file (see README).")

    keys = st.session_state.api_keys

    with st.expander("ðŸ¤– Anthropic (Claude AI â€” Script Generation)", expanded=True):
        keys["anthropic"] = st.text_input(
            "Anthropic API Key", value=keys["anthropic"], type="password",
            help="Get yours at https://console.anthropic.com",
        )

    with st.expander("ðŸŽ™ï¸ ElevenLabs (AI Voiceover)"):
        keys["elevenlabs"] = st.text_input(
            "ElevenLabs API Key", value=keys["elevenlabs"], type="password",
            help="Get yours at https://elevenlabs.io. Leave blank to use free gTTS fallback.",
        )

    with st.expander("ðŸ“¹ Pexels (Stock Footage)", expanded=True):
        keys["pexels"] = st.text_input(
            "Pexels API Key", value=keys["pexels"], type="password",
            help="Free at https://www.pexels.com/api/",
        )

    with st.expander("ðŸ“º YouTube"):
        st.markdown("YouTube requires OAuth2 credentials. [Setup guide â†’](https://developers.google.com/youtube/v3/guides/uploading_a_video)")
        keys["youtube_creds"] = st.text_input(
            "Path to credentials JSON", value=keys["youtube_creds"],
            placeholder="/path/to/client_secrets.json",
        )
        st.caption("Place your OAuth2 `client_secrets.json` on the server and provide the path above.")

    with st.expander("ðŸ“¸ Instagram"):
        keys["instagram_user"] = st.text_input("Instagram Username", value=keys["instagram_user"])
        keys["instagram_pass"] = st.text_input("Instagram Password", value=keys["instagram_pass"], type="password")
        st.caption("Uses instagrapi. Requires a regular Instagram account (not just Creator Studio).")

    with st.expander("ðŸŽµ TikTok"):
        keys["tiktok_session"] = st.text_input(
            "TikTok sessionid cookie", value=keys["tiktok_session"], type="password",
            help="Extract from browser cookies after logging in to tiktok.com",
        )
        st.caption("Paste your `sessionid` cookie value from TikTok browser session.")

    with st.expander("ðŸ¦ Twitter / X"):
        col1, col2 = st.columns(2)
        with col1:
            keys["twitter_key"]          = st.text_input("API Key",          value=keys["twitter_key"],          type="password")
            keys["twitter_token"]        = st.text_input("Access Token",     value=keys["twitter_token"],        type="password")
        with col2:
            keys["twitter_secret"]       = st.text_input("API Secret",       value=keys["twitter_secret"],       type="password")
            keys["twitter_token_secret"] = st.text_input("Access Token Secret", value=keys["twitter_token_secret"], type="password")
        st.caption("Get keys at https://developer.twitter.com â€” requires Elevated or Basic access for video upload.")

    st.session_state.api_keys = keys

    if st.button("ðŸ’¾ Save to .env file (local dev only)", use_container_width=True):
        env_lines = [
            f'ANTHROPIC_API_KEY="{keys["anthropic"]}"',
            f'ELEVENLABS_API_KEY="{keys["elevenlabs"]}"',
            f'PEXELS_API_KEY="{keys["pexels"]}"',
            f'YOUTUBE_CREDENTIALS_PATH="{keys["youtube_creds"]}"',
            f'INSTAGRAM_USERNAME="{keys["instagram_user"]}"',
            f'INSTAGRAM_PASSWORD="{keys["instagram_pass"]}"',
            f'TIKTOK_SESSION_ID="{keys["tiktok_session"]}"',
            f'TWITTER_API_KEY="{keys["twitter_key"]}"',
            f'TWITTER_API_SECRET="{keys["twitter_secret"]}"',
            f'TWITTER_ACCESS_TOKEN="{keys["twitter_token"]}"',
            f'TWITTER_ACCESS_TOKEN_SECRET="{keys["twitter_token_secret"]}"',
        ]
        with open(".env", "w") as f:
            f.write("\n".join(env_lines))
        st.success("âœ… Saved to .env")

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PAGE: POST HISTORY
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
elif page == "ðŸ“‹ Post History":
    st.title("ðŸ“‹ Post History")
    history = st.session_state.post_history

    if not history:
        st.info("No posts yet. Generate and post a video to see history here.")
    else:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("ðŸ—‘ï¸ Clear History"):
                st.session_state.post_history = []
                st.rerun()

        df = pd.DataFrame([
            {
                "Timestamp": p.get("timestamp", "â€”"),
                "Topic":     p.get("topic", "â€”"),
                "Platforms": ", ".join(p.get("platforms", [])),
                "Status":    "âœ… Posted" if p.get("results") else "âš ï¸ Partial",
            }
            for p in reversed(history)
        ])
        st.dataframe(df, use_container_width=True, height=400)

        for post in reversed(history[-5:]):
            with st.expander(f"ðŸ“„ {post.get('topic','â€”')} â€” {post.get('timestamp','â€”')}"):
                if post.get("results"):
                    for platform, result in post["results"].items():
                        icon = "âœ…" if result.get("success") else "âŒ"
                        st.write(f"{icon} **{platform}**: {result.get('message','â€”')}")
                        if result.get("url"):
                            st.write(f"   ðŸ”— [View post]({result['url']})")
