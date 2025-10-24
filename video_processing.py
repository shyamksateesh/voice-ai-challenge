import moviepy.editor as mp
import numpy as np
import config
import os

def generate_phrase_video(input_path, segments, output_filename, is_video_input, vocal_track_path, log_callback):
    """
    Generates a lyrics video with polished, readable, phrase-level subtitles
    that dynamically resize and do NOT overlap.
    """
    if not segments:
        log_callback("No segments to process. Skipping video generation.")
        return

    log_callback("Starting video generation (phrase-by-phrase)...")
    
    # Determine which audio to use
    if config.REPLACE_AUDIO_WITH_VOCALS and vocal_track_path:
        log_callback("Replacing video audio with separated vocals.")
        final_audio_clip = mp.AudioFileClip(vocal_track_path)
    else:
        log_callback("Using original video audio.")
        # Load audio from the original input
        if is_video_input:
            final_audio_clip = mp.VideoFileClip(input_path).audio
        else:
            final_audio_clip = mp.AudioFileClip(input_path)

    # Load the original media to get duration and audio
    if is_video_input:
        base_clip = mp.VideoFileClip(input_path)
        
        # Downscale video to 720p for faster, consistent rendering
        if base_clip.size[1] > 720:
            log_callback(f"Downscaling video from {base_clip.size[1]}p to 720p...")
            base_clip = base_clip.resize(height=720)
        
        media_size = base_clip.size
    else:
        # Audio-only is already capped at our default
        media_size = (1280, 720) # Default to 720p for audio-only
        base_clip = mp.ColorClip(
            size=media_size,
            color=[0, 0, 0],
            duration=final_audio_clip.duration
        )
    
    # Calculate dynamic font size based on video width
    dynamic_font_size = int(media_size[0] * config.RELATIVE_FONT_SIZE)
    log_callback(f"Video width: {media_size[0]}px. Setting font size to {dynamic_font_size}px.")
    
    text_clips = []
    
    # Determine position based on input type
    position = 'center' if not is_video_input else ('center', config.SUBTITLE_Y_POSITION)
    
    log_callback("Compositing text clips...")
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
        ).set_duration(duration).set_start(start_time).set_position(position, relative=True)
        
        text_clips.append(txt_clip)

    final_clip = mp.CompositeVideoClip([base_clip] + text_clips)
    
    # Set the new audio
    final_clip = final_clip.set_audio(final_audio_clip)

    # Write the final video file with hardware acceleration
    try:
        log_callback("Writing final video file... (Using hardware acceleration)")
        final_clip.write_videofile(
            output_filename,
            codec="h264_videotoolbox", # FAST: Use Apple's hardware encoder
            audio_codec="aac",
            fps=24,
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            preset="fast",
            threads=8,
            logger='bar' # This will still go to console, which is fine
        )
        log_callback(f"Success! Lyrics video successfully generated: '{output_filename}'")
    except Exception as e:
        log_callback(f"Hardware acceleration failed: {e}")
        log_callback("Trying again with software encoder (this will be much slower)...")
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
        log_callback(f"Success! Lyrics video successfully generated: '{output_filename}'")
    finally:
        # Close clips to free up memory
        if 'base_clip' in locals():
            base_clip.close()
        if 'final_audio_clip' in locals():
            final_audio_clip.close()
        final_clip.close()


# --- Karaoke (Wipe Text) Function ---

def create_karaoke_clip(segment, media_size, dynamic_font_size, is_video_input):
    """
    Creates a single moviepy clip for one lyrical segment
    with a word-by-word highlighting (snap) effect.
    """
    seg_start = max(0, segment.get("start", 0))
    seg_end = segment.get("end", seg_start + 2)
    seg_duration = max(0.5, seg_end - seg_start)
    phrase = segment.get("text", "").strip()
    words = segment.get("words", [])

    if not phrase:
        return None

    # Determine position
    position = 'center' if not is_video_input else ('center', config.SUBTITLE_Y_POSITION)

    # --- Create Base Text (unhighlighted background) ---
    base_clip = (
        mp.TextClip(
            phrase,
            fontsize=dynamic_font_size,
            color=config.BG_COLOR,
            font=config.KARAOKE_FONT,
            method="caption",
            size=(media_size[0] * 0.9, None),
        )
        .set_position(position, relative=True)
        .set_duration(seg_duration)
        .set_start(seg_start)
    )

    # --- Create Highlighted Text (foreground) ---
    highlight_clip = (
        mp.TextClip(
            phrase,
            fontsize=dynamic_font_size,
            color=config.FONT_COLOR,
            font=config.KARAOKE_FONT,
            method="caption",
            size=(media_size[0] * 0.9, None),
        )
        .set_position(position, relative=True)
        .set_duration(seg_duration)
        .set_start(seg_start)
    )

    if not words:
        return highlight_clip

    # --- Pre-calculate word timings and character positions ---
    total_chars = len(phrase)
    word_timings = []
    char_idx = 0
    
    # Clean up phrase and word text for more reliable indexing
    clean_phrase = " ".join(phrase.split())
    
    for w in words:
        word_text = w.get("text", "").strip()
        w_start = w.get("start")
        if not word_text or w_start is None:
            continue
            
        try:
            # Find the word's start index in the phrase
            word_start_index = clean_phrase.index(word_text, char_idx)
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
        
        width = int(base_clip.w * width_percent)
        width = np.clip(width, 0, base_clip.w)
        
        mask = np.zeros(base_clip.size, dtype=np.uint8)
        mask_h = base_clip.h
        mask_w = base_clip.w

        # Check if text is centered and find text-box boundaries
        # This is a simple approximation
        text_width = base_clip.w * 0.9 # Since size is 90%
        margin = (mask_w - text_width) / 2
        
        # Apply mask only to the text area
        mask[:, int(margin):int(margin + width)] = 1
        return mask.astype(bool) # Return as boolean mask

    # Create the animated mask clip
    mask_clip = mp.VideoClip(make_frame, duration=seg_duration, ismask=True)
    highlight_clip = highlight_clip.set_mask(mask_clip)

    return mp.CompositeVideoClip([base_clip, highlight_clip], size=media_size)


def generate_karaoke_video(input_path, segments, output_filename, is_video_input, vocal_track_path, log_callback):
    """
    Generates a lyrics video with word-by-word karaoke highlighting.
    """
    if not segments:
        log_callback("No segments to process. Skipping video generation.")
        return

    log_callback("Starting video generation (karaoke wipe)...")

    # Determine which audio to use
    if config.REPLACE_AUDIO_WITH_VOCALS and vocal_track_path:
        log_callback("Replacing video audio with separated vocals.")
        final_audio_clip = mp.AudioFileClip(vocal_track_path)
    else:
        log_callback("Using original video audio.")
        if is_video_input:
            final_audio_clip = mp.VideoFileClip(input_path).audio
        else:
            final_audio_clip = mp.AudioFileClip(input_path)

    # Load the base video or create a black background
    if is_video_input:
        base_clip = mp.VideoFileClip(input_path)
        if base_clip.size[1] > 720:
            log_callback(f"Downscaling video from {base_clip.size[1]}p to 720p...")
            base_clip = base_clip.resize(height=720)
        media_size = base_clip.size
    else:
        media_size = (1280, 720)
        base_clip = mp.ColorClip(
            media_size, 
            color=[0, 0, 0], 
            duration=final_audio_clip.duration
        )
    
    # Calculate dynamic font size
    dynamic_font_size = int(media_size[0] * config.RELATIVE_FONT_SIZE)
    log_callback(f"Video width: {media_size[0]}px. Setting font size to {dynamic_font_size}px.")

    text_clips = []
    log_callback("Compositing karaoke text clips...")
    for seg in segments:
        clip = create_karaoke_clip(seg, media_size, dynamic_font_size, is_video_input)
        if clip:
            text_clips.append(clip)
            
    if not text_clips:
        log_callback("No valid text clips were created. Aborting.")
        return

    final_clip = mp.CompositeVideoClip([base_clip] + text_clips)
    final_clip = final_clip.set_audio(final_audio_clip)

    # Write final video with hardware acceleration
    try:
        log_callback("Writing final video file... (Using hardware acceleration)")
        final_clip.write_videofile(
            output_filename,
            codec="h264_videotoolbox",
            audio_codec="aac",
            fps=24,
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            preset="fast",
            threads=8,
            logger='bar'
        )
        log_callback(f"Success! Karaoke video created: '{output_filename}'")
    except Exception as e:
        log_callback(f"Hardware acceleration failed: {e}")
        log_callback("Trying again with software encoder (this will be much slower)...")
        final_clip.write_videofile(
            output_filename,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            preset="fast",
            threads=8,
            logger='bar'
        )
        log_callback(f"Success! Karaoke video created: '{output_filename}'")
    finally:
        # Close clips to free up memory
        if 'base_clip' in locals():
            base_clip.close()
        if 'final_audio_clip' in locals():
            final_audio_clip.close()
        final_clip.close()
