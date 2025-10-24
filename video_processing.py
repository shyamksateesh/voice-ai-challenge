import moviepy.editor as mp # type: ignore
import config # Import our settings
import numpy as np # type: ignore

# <<< FIX: Pass is_video_input
def generate_phrase_video(input_path, segments, output_filename, is_video_input, vocal_separation_succeeded=False):
    """
    Generates a lyrics video with polished, readable, phrase-level subtitles
    that dynamically resize and do NOT overlap.
    """
    if not segments:
        print("No segments to process. Skipping video generation.")
        return

    print("Starting video generation...")
    # Load the original media
    if is_video_input:
        base_clip = mp.VideoFileClip(input_path)
        
        # Downscale video to 720p for faster, consistent rendering
        if base_clip.size[1] > 720:
            print(f"Downscaling video from {base_clip.size[1]}p to 720p...")
            base_clip = base_clip.resize(height=720)
        
        media_size = base_clip.size
    else:
        audio_clip = mp.AudioFileClip(input_path)
        media_size = (1280, 720) # Default to 720p
        base_clip = mp.ColorClip(
            size=media_size,
            color=[0, 0, 0],
            duration=audio_clip.duration
        ).set_audio(audio_clip)
    
    # Calculate dynamic font size from config
    dynamic_font_size = int(media_size[0] * config.RELATIVE_FONT_SIZE)
    print(f"Video width: {media_size[0]}px. Setting font size to {dynamic_font_size}px.")
    
    # <<< FIX: Set position based on input type
    if is_video_input:
        subtitle_position = ('center', config.SUBTITLE_Y_POSITION)
        is_relative_pos = True
    else:
        # Center it for audio-only
        subtitle_position = 'center'
        is_relative_pos = False

    text_clips = []
    
    # Iterate with an index to prevent overlaps
    for i, seg in enumerate(segments):
        start_time = seg['start']
        text = seg['text'].strip()

        # Determine the correct duration
        if i + 1 < len(segments):
            next_start_time = segments[i+1]['start']
            duration = next_start_time - start_time
        else:
            duration = seg['end'] - start_time

        if duration <= 0 or not text:
            continue

        # Create a styled TextClip for the segment
        txt_clip = mp.TextClip(
            text,
            fontsize=dynamic_font_size,
            color=config.FONT_COLOR,
            font=config.FONT_FAMILY,
            bg_color=config.FONT_BACKGROUND, 
            size=(media_size[0] * 0.9, None), # 90% width
            method='caption'
        ).set_duration(duration).set_start(start_time).set_position(subtitle_position, relative=is_relative_pos) # <<< FIX: Use new variables
        
        text_clips.append(txt_clip)

    final_clip = mp.CompositeVideoClip([base_clip] + text_clips)
    
    # <<< FIX: Replace the audio if the flag is set
    # --- Set Final Audio Track ---
    if vocal_separation_succeeded and config.REPLACE_AUDIO_WITH_VOCALS:
        print("Replacing original audio with separated vocals...")
        try:
            # Load the separated vocals
            vocal_audio = mp.AudioFileClip(config.VOCALS_WAV_FILE)
            final_clip = final_clip.set_audio(vocal_audio)
        except Exception as e:
            print(f"Warning: Could not load vocal audio. Defaulting to original. Error: {e}")
            if is_video_input:
                final_clip = final_clip.set_audio(base_clip.audio)
    else:
        # Default: Use the original audio from the video
        if is_video_input:
             final_clip = final_clip.set_audio(base_clip.audio)

    # Write the final video file with hardware acceleration
    try:
        print("Writing final video file... (Using hardware acceleration)")
        final_clip.write_videofile(
            output_filename,
            codec="h264_videotoolbox", # FAST: Use Apple's hardware encoder
            audio_codec="aac",
            fps=24,
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            preset="fast",
            threads=8,
            logger='bar'
        )
        print(f"\nSuccess! Lyrics video successfully generated: '{output_filename}'")
    except Exception as e:
        print(f"\nHardware acceleration failed: {e}")
        print("Trying again with software encoder (this will be much slower)...")
        # Fallback to software encoding
        final_clip.write_videofile(
            output_filename,
            codec="libx264", # SLOW: Software encoder
            audio_codec="aac",
            fps=24,
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            preset="fast",
            threads=8,
            logger='bar'
        )
        print(f"\nSuccess! Lyrics video successfully generated: '{output_filename}'")

# -----------------------------------------------------------------
# --- KARAOKE WIPE FUNCTIONS ---
# -----------------------------------------------------------------

# <<< FIX: Pass is_video_input
def create_karaoke_clip(segment, media_size, dynamic_font_size, is_video_input):
    """Creates a single text clip with a word-by-word highlighting animation."""
    seg_start = max(0, segment.get("start", 0))
    seg_end = segment.get("end", seg_start + 2)
    seg_duration = max(0.5, seg_end - seg_start)
    phrase = segment.get("text", "").strip()
    words = segment.get("words", [])

    if not phrase:
        return None

    # <<< FIX: Set position based on input type
    if is_video_input:
        subtitle_position = ('center', config.SUBTITLE_Y_POSITION)
        is_relative_pos = True
    else:
        # Center it for audio-only
        subtitle_position = 'center'
        is_relative_pos = False

    # Create base text (unhighlighted background)
    base_clip = (
        mp.TextClip(
            phrase,
            fontsize=dynamic_font_size,
            color=config.BG_COLOR,
            font=config.KARAOKE_FONT, # Use monospace font from config
            method="caption", # <<< FIX: Use caption for robust sizing
            size=(media_size[0] * 0.9, None)
        )
        .set_position(subtitle_position, relative=is_relative_pos) # <<< FIX: Use new variables
        .set_duration(seg_duration)
        .set_start(seg_start)
    )

    # --- Create Highlighted Text (foreground) ---
    highlight_clip = (
        mp.TextClip(
            phrase,
            fontsize=dynamic_font_size,
            color=config.FONT_COLOR,
            font=config.KARAOKE_FONT, # Use monospace font from config
            method="caption", # <<< FIX: Use caption for robust sizing
            size=(media_size[0] * 0.9, None)
        )
        .set_position(subtitle_position, relative=is_relative_pos) # <<< FIX: Use new variables
        .set_duration(seg_duration)
        .set_start(seg_start)
    )

    if not words:
        # Fallback if no word-level timestamps
        return highlight_clip

    # --- Pre-calculate word timings and character positions ---
    total_chars = len(phrase)
    word_timings = []
    char_idx = 0
    for w in words:
        word_text = w.get("text", "").strip()
        w_start = w.get("start")
        if not word_text or w_start is None:
            continue
            
        try:
            word_start_index = phrase.index(word_text, char_idx)
            char_end_index = word_start_index + len(word_text)
            word_timings.append((w_start, char_end_index))
            char_idx = char_end_index
        except ValueError:
            continue 

    # --- Animation mask: reveals text word by word ---
    def make_frame(t):
        current_time_abs = seg_start + t
        
        chars_to_highlight = 0
        for w_start, char_end_index in word_timings:
            if current_time_abs >= w_start:
                chars_to_highlight = char_end_index
            else:
                break
        
        if total_chars == 0:
            width_percent = 0
        else:
            width_percent = chars_to_highlight / total_chars
        
        width = int(base_clip.size[0] * width_percent)
        width = np.clip(width, 0, base_clip.size[0])
        
        mask = np.zeros((base_clip.size[1], base_clip.size[0]), dtype=np.uint8)
        mask[:, :width] = 255
        return mask

    mask_clip = mp.VideoClip(make_frame, duration=seg_duration, ismask=True)
    highlight_clip = highlight_clip.set_mask(mask_clip)

    return mp.CompositeVideoClip([base_clip, highlight_clip], size=media_size)


# <<< FIX: Add new parameter: vocal_separation_succeeded
def generate_karaoke_video(input_path, segments, output_filename, is_video_input, vocal_separation_succeeded=False):
    """
    Generates a lyrics video with word-by-word karaoke highlighting,
    capping quality at 720p for speed.
    """
    if not segments:
        print("No transcription segments found.")
        return

    print("Generating karaoke video...")

    if is_video_input:
        base_clip = mp.VideoFileClip(input_path)
        
        if base_clip.size[1] > 720:
            print(f"Downscaling video from {base_clip.size[1]}p to 720p...")
            base_clip = base_clip.resize(height=720)
        
        media_size = base_clip.size
    else:
        audio_clip = mp.AudioFileClip(input_path)
        media_size = (1280, 720)
        base_clip = mp.ColorClip(media_size, color=[0, 0, 0], duration=audio_clip.duration).set_audio(audio_clip)

    dynamic_font_size = int(media_size[0] * config.RELATIVE_FONT_SIZE)
    print(f"Video width: {media_size[0]}px. Setting font size to {dynamic_font_size}px.")

    text_clips = []
    for seg in segments:
        # <<< FIX: Pass is_video_input down to the clip creator
        clip = create_karaoke_clip(seg, media_size, dynamic_font_size, is_video_input)
        if clip:
            text_clips.append(clip)

    final_clip = mp.CompositeVideoClip([base_clip] + text_clips)
    
    # <<< FIX: Replace the audio if the flag is set
    # --- Set Final Audio Track ---
    if vocal_separation_succeeded and config.REPLACE_AUDIO_WITH_VOCALS:
        print("Replacing original audio with separated vocals...")
        try:
            # Load the separated vocals
            vocal_audio = mp.AudioFileClip(config.VOCALS_WAV_FILE)
            final_clip = final_clip.set_audio(vocal_audio)
        except Exception as e:
            print(f"Warning: Could not load vocal audio. Defaulting to original. Error: {e}")
            if is_video_input:
                final_clip = final_clip.set_audio(base_clip.audio)
    else:
        # Default: Use the original audio from the video
        if is_video_input:
             final_clip = final_clip.set_audio(base_clip.audio)

    # --- Write final video with hardware acceleration ---
    try:
        print("Writing final video file... (Using hardware acceleration)")
        final_clip.write_videofile(
            output_filename,
            codec="h264_videotoolbox",
            audio_codec="aac",
            fps=24,
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            preset="fast",
            threads=8,
            logger='bar'
        )
        print(f"\nSuccess! Lyrics video successfully generated: '{output_filename}'")
    except Exception as e:
        print(f"\nHardware acceleration failed: {e}")
        print("Trying again with software encoder (this will be much slower)...")
        final_clip.write_videofile(
            output_filename,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            preset="fast",
            threads=8,
            logger='bar'
        )
        print(f"\nSuccess! Lyrics video successfully generated: '{output_filename}'")


