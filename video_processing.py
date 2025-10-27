import moviepy.editor as mp
import numpy as np
import os
import config # Import config for style constants
import math # Import math for ceiling function

# --- generate_phrase_video Function (Remains the same) ---
def generate_phrase_video(input_path, segments, output_filename, is_video_input, log_callback=print, audio_path_override=None):

    if not segments:
        log_callback("No segments to process. Skipping video generation.")
        return

    log_callback("Starting video generation (phrase-by-phrase)...")
    final_audio_clip = None
    base_clip_duration = 0

    if is_video_input:
        try:
            base_clip = mp.VideoFileClip(input_path)
            # <<< FIX: Ensure duration is read correctly >>>
            base_clip_duration = base_clip.duration if base_clip.duration is not None else 0
        except Exception as e:
            log_callback(f"Error loading base video clip: {e}")
            return

        if audio_path_override and os.path.exists(audio_path_override):
             log_callback(f"Overriding video audio with: {os.path.basename(audio_path_override)}")
             try: final_audio_clip = mp.AudioFileClip(audio_path_override)
             except Exception as e:
                 log_callback(f"Warning: Could not load override audio: {e}")
                 # <<< FIX: Check if base_clip has audio before assigning >>>
                 final_audio_clip = base_clip.audio if base_clip and hasattr(base_clip, 'audio') else None
        else:
             log_callback("Using original video audio.")
             final_audio_clip = base_clip.audio if base_clip and hasattr(base_clip, 'audio') else None


        # Downscale for performance
        if base_clip and base_clip.size and base_clip.size[1] > 720:
            log_callback(f"Downscaling video from {base_clip.size[1]}p to 720p...")
            base_clip = base_clip.resize(height=720)
        media_size = base_clip.size if base_clip else (1280, 720) # Fallback size

    else: # Audio input
        try:
            if audio_path_override and os.path.exists(audio_path_override):
                 log_callback(f"Using override audio: {os.path.basename(audio_path_override)}")
                 final_audio_clip = mp.AudioFileClip(audio_path_override)
            else:
                 log_callback("Using original input audio.")
                 final_audio_clip = mp.AudioFileClip(input_path)

            base_clip_duration = final_audio_clip.duration if final_audio_clip else 0
            if base_clip_duration <= 0:
                 log_callback("Error: Audio clip has zero or negative duration.")
                 return

            media_size = (1280, 720)
            base_clip = mp.ColorClip(size=media_size, color=[0, 0, 0], duration=base_clip_duration)
        except Exception as e:
             log_callback(f"Error loading audio clip or creating base ColorClip: {e}")
             return

    # Use dynamic font for phrase video
    dynamic_font_size = int(media_size[0] * config.RELATIVE_FONT_SIZE)
    log_callback(f"Video width: {media_size[0]}px. Setting font size to {dynamic_font_size}px.")

    text_clips = []
    log_callback("Compositing text clips...")
    last_segment_end = 0 # <<< FIX: Initialize last_segment_end for accurate timing calc >>>
    for i, seg in enumerate(segments):
        start_time = seg.get('start', last_segment_end) # <<< Use last_segment_end as default
        text = seg.get('text', "").strip()

        # <<< FIX: More robust duration calculation >>>
        seg_end_time = seg.get('end', start_time + 2) # Default end if missing
        next_start_time = segments[i+1].get('start', base_clip_duration) if i + 1 < len(segments) else base_clip_duration
        # Clip should end either at its own end time, the next clip's start, or video end, whichever is earliest
        actual_end_time = min(seg_end_time, next_start_time, base_clip_duration)
        duration = max(0.01, actual_end_time - start_time) # Ensure positive duration

        # Update last_segment_end for the next iteration
        last_segment_end = actual_end_time # Use the calculated end time

        # Timing checks
        if start_time >= base_clip_duration:
             log_callback(f"Skipping segment '{text[:30]}...' starting after video end ({start_time:.2f}s >= {base_clip_duration:.2f}s)")
             continue
        # <<< FIX: Adjust trimming logic >>>
        if start_time + duration > base_clip_duration + 0.01: # Add small tolerance
             duration = base_clip_duration - start_time
             log_callback(f"Trimming duration of segment '{text[:30]}...' to fit video length ({duration:.2f}s)")
             if duration <= 0.01: continue


        position = 'center' if not is_video_input else ('center', config.SUBTITLE_Y_POSITION)
        relative_pos = False if not is_video_input else True

        try:
            txt_clip = mp.TextClip(
                text,
                fontsize=dynamic_font_size, # Use dynamic font here
                color=config.FONT_COLOR,
                font=config.FONT_FAMILY,
                bg_color=config.FONT_BACKGROUND,
                size=(media_size[0] * 0.9, None),
                method='caption' # Allow wrapping for phrase video
            ).set_duration(duration).set_start(start_time).set_position(position, relative=relative_pos)

            text_clips.append(txt_clip)
        except Exception as clip_err:
             log_callback(f"Warning: Could not create text clip for segment '{text[:30]}...': {clip_err}")

    if not text_clips:
         log_callback("Warning: No valid text clips were generated.")
         if 'base_clip' not in locals() or base_clip is None:
              log_callback("Error: Base clip not defined.")
              return
         final_clip = base_clip # Use base if no text
    else:
        log_callback(f"Final Phrase Composite: Base clip type={type(base_clip).__name__}, Size={media_size}, Duration={base_clip_duration:.2f}, Num text clips={len(text_clips)}")
        if base_clip is None:
            log_callback("Error: Base clip is None before final compositing.")
            return
        # <<< FIX: Explicitly set composite size and duration >>>
        final_clip = mp.CompositeVideoClip([base_clip] + text_clips, size=media_size).set_duration(base_clip_duration)

    if final_audio_clip:
        try:
            audio_dur = final_audio_clip.duration if final_audio_clip and final_audio_clip.duration is not None else 0
            clip_dur = final_clip.duration if final_clip and final_clip.duration is not None else 0
            safe_duration = min(audio_dur, clip_dur)

            if safe_duration > 0:
                safe_audio = final_audio_clip.subclip(0, safe_duration)
                final_clip = final_clip.set_audio(safe_audio)
                log_callback(f"Set final audio duration to {final_clip.audio.duration:.2f}s (matching video duration {final_clip.duration:.2f}s)")
            else:
                 log_callback(f"Warning: Calculated safe audio duration is zero or less ({audio_dur=}, {clip_dur=}). No audio set.")
                 final_clip = final_clip.set_audio(None)
        except Exception as audio_err:
             log_callback(f"Warning: Could not set final audio clip: {audio_err}")
             final_clip = final_clip.set_audio(None)
    else:
        log_callback("Warning: No audio track available for final video.")
        final_clip = final_clip.set_audio(None)

    # Write the final video file
    try:
        log_callback("Writing final video file... (Using hardware acceleration)")
        final_clip.write_videofile(
            output_filename, codec="h264_videotoolbox", audio_codec="aac", fps=24,
            temp_audiofile='temp-audio.m4a', remove_temp=True, preset="fast", threads=8, logger='bar'
        )
        log_callback(f"Success! Lyrics video successfully generated: '{output_filename}'")
    except Exception as e:
        log_callback(f"Hardware acceleration failed: {e}")
        log_callback("Trying again with software encoder (this will be much slower)...")
        final_clip.write_videofile(
            output_filename, codec="libx264", audio_codec="aac", fps=24,
            temp_audiofile='temp-audio.m4a', remove_temp=True, preset="fast", threads=8, logger='bar'
        )
        log_callback(f"Success! Lyrics video successfully generated: '{output_filename}'")
    finally:
        if 'base_clip' in locals() and base_clip and hasattr(base_clip, 'close'): base_clip.close()
        if 'final_audio_clip' in locals() and final_audio_clip and hasattr(final_audio_clip, 'close'): final_audio_clip.close()
        if 'final_clip' in locals() and final_clip and hasattr(final_clip, 'close'): final_clip.close()
        for tc in text_clips:
             if hasattr(tc, 'close'): tc.close()


# --- UPDATED create_karaoke_clip Function: Simplified Positioning ---
def create_karaoke_clip(segment, media_size, is_video_input, log_callback=print):
    """
    Creates tuple of (base_clip, highlight_clip_with_mask) for one segment (single line).
    Applies position only on the final composite returned.
    """
    seg_start = segment.get("start", 0)
    seg_end = segment.get("end", seg_start + 2)
    seg_duration = max(0.1, seg_end - seg_start)
    phrase = segment.get("text", "").strip()
    words = segment.get("words", [])

    if not phrase:
        log_callback(f"Karaoke: Skipping empty phrase at {seg_start:.2f}s.")
        return None

    log_callback(f"Karaoke: Processing segment '{phrase[:30]}...' Start={seg_start:.2f}s, Duration={seg_duration:.2f}s")

    fixed_font_size = int(media_size[0] * 0.04)

    # Define text properties (without position initially)
    base_text_kwargs = {
        "fontsize": fixed_font_size,
        "font": config.KARAOKE_FONT,
        "method": "label",
        "color": config.BG_COLOR,
    }
    highlight_text_kwargs = {
        "fontsize": fixed_font_size,
        "font": config.KARAOKE_FONT,
        "method": "label",
        "color": config.FONT_COLOR,
        "bg_color": config.FONT_BACKGROUND
    }

    base_clip = None
    highlight_clip = None
    final_composite = None # The clip to be returned

    # --- Create Base Text ---
    try:
        # Create without position to get natural size
        base_clip = mp.TextClip(phrase, **base_text_kwargs).set_duration(seg_duration)
        base_clip_size = base_clip.size # Store natural size
        log_callback(f"Karaoke: Base clip natural size={base_clip.size}")
    except Exception as clip_err:
        log_callback(f"Warning: Could not create base karaoke text clip for '{phrase[:30]}...': {clip_err}")
        return None

    # --- Create Highlighted Text ---
    try:
        # Create without position
        highlight_clip = mp.TextClip(phrase, **highlight_text_kwargs).set_duration(seg_duration)
        log_callback(f"Karaoke: Highlight clip natural size={highlight_clip.size}")
    except Exception as clip_err:
         log_callback(f"Warning: Could not create highlight karaoke text clip for '{phrase[:30]}...': {clip_err}")
         # If highlight fails, create a composite with just the base clip (positioned)
         position = 'center' if not is_video_input else ('center', config.SUBTITLE_Y_POSITION)
         relative_pos = False if not is_video_input else True
         if not is_video_input: # Recalculate center Y
             y_pos = (media_size[1] - base_clip_size[1]) / 2
             position = ('center', y_pos)
         final_composite = base_clip.set_position(position, relative=relative_pos).set_start(seg_start)
         log_callback(f"Karaoke: Highlight failed, returning positioned base clip. Pos={final_composite.pos}")
         return final_composite # Return positioned base clip


    # --- Apply Mask if words exist ---
    if not words:
        log_callback(f"No word timestamps for segment '{phrase[:30]}...', using static highlight.")
        # If no words, composite the base and highlight clips, then position
        final_composite = mp.CompositeVideoClip([base_clip, highlight_clip])

    else: # Apply mask
        # --- Pre-calculate word timings ---
        total_chars = len(phrase)
        word_timings = []
        char_idx = 0
        valid_words_found = False
        log_callback(f"Karaoke: Found {len(words)} words in segment.")
        for w_idx, w in enumerate(words):
            word_text = w.get("word", "").strip()
            w_start = w.get("start")
            w_end = w.get("end")
            if not word_text or w_start is None or w_end is None: continue
            try:
                word_start_index = phrase.index(word_text, char_idx)
                relative_w_start = max(0, w_start - seg_start)
                char_end_index = word_start_index + len(word_text)
                word_timings.append((relative_w_start, char_end_index))
                char_idx = word_start_index + len(word_text)
                if char_idx < total_chars and phrase[char_idx] == ' ': char_idx += 1
                valid_words_found = True
            except ValueError:
                 log_callback(f"Warning: Word '{word_text}' from alignment not found...")
                 char_idx += len(word_text) + 1
                 continue
        if not valid_words_found:
             log_callback(f"No valid word timings could be mapped...")
             final_composite = mp.CompositeVideoClip([base_clip, highlight_clip]) # Fallback composite
        else:
            # --- Animation mask ---
            def make_frame(t):
                chars_to_highlight = 0
                for relative_w_start, char_end_index in word_timings:
                    if t >= relative_w_start: chars_to_highlight = char_end_index
                    else: break
                if total_chars == 0: width_percent = 0
                else: width_percent = chars_to_highlight / total_chars
                clip_width_pixels = base_clip_size[0] # Use natural size for calculation
                width = int(clip_width_pixels * width_percent)
                width = np.clip(width, 0, clip_width_pixels)
                mask = np.zeros((base_clip_size[1], clip_width_pixels), dtype=np.uint8)
                mask[:, :width] = 255
                return mask

            try:
                mask_clip = mp.VideoClip(make_frame, duration=seg_duration, ismask=True)
                # Apply mask - position will be set on the final composite
                highlight_clip_masked = highlight_clip.set_mask(mask_clip)
                log_callback(f"Karaoke: Created masked highlight for '{phrase[:30]}...'")
                # Create composite *without* position here
                final_composite = mp.CompositeVideoClip([base_clip, highlight_clip_masked])

            except Exception as mask_err:
                log_callback(f"Error creating animation mask for '{phrase[:30]}...': {mask_err}")
                final_composite = mp.CompositeVideoClip([base_clip, highlight_clip]) # Fallback composite


    # --- Apply final position and timing ---
    if final_composite is None:
         log_callback("Karaoke: final_composite is None, cannot proceed.")
         return None

    # Calculate final position based on the composite's size
    final_clip_size = final_composite.size
    position = 'center' if not is_video_input else ('center', config.SUBTITLE_Y_POSITION)
    relative_pos = False if not is_video_input else True
    if not is_video_input:
        y_pos = (media_size[1] - final_clip_size[1]) / 2
        position = ('center', y_pos)
        log_callback(f"Karaoke: Final composite recentered Y to {y_pos:.2f}")

    # Set position and timing on the final composite clip
    final_composite = final_composite.set_position(position, relative=relative_pos).set_start(seg_start).set_duration(seg_duration)

    log_callback(f"Karaoke: Returning final segment clip - Start={final_composite.start:.2f}s, Duration={final_composite.duration:.2f}s, Size={final_composite.size}, Pos={final_composite.pos}")
    return final_composite


# --- generate_karaoke_video Function (No changes needed here) ---
def generate_karaoke_video(input_path, segments, output_filename, is_video_input, log_callback=print, audio_path_override=None):
    if not segments:
        log_callback("No segments to process. Skipping karaoke video generation.")
        return

    log_callback("Starting karaoke video generation (word-by-word)...")
    final_audio_clip = None
    base_clip_duration = 0
    base_clip_layer = None

    if is_video_input:
        log_callback("Karaoke: Processing VIDEO input.")
        try:
            base_clip_layer = mp.VideoFileClip(input_path)
            # <<< FIX: Ensure duration is read correctly >>>
            base_clip_duration = base_clip_layer.duration if base_clip_layer.duration is not None else 0
            log_callback(f"Karaoke: Loaded VIDEO base layer. Duration={base_clip_duration:.2f}s, Size={base_clip_layer.size}")
        except Exception as e:
            log_callback(f"Error loading base video clip: {e}")
            return

        if audio_path_override and os.path.exists(audio_path_override):
             log_callback(f"Overriding video audio with: {os.path.basename(audio_path_override)}")
             try: final_audio_clip = mp.AudioFileClip(audio_path_override)
             except Exception as e:
                 log_callback(f"Warning: Could not load override audio: {e}")
                 # <<< FIX: Check if base_clip_layer has audio >>>
                 final_audio_clip = base_clip_layer.audio if base_clip_layer and hasattr(base_clip_layer, 'audio') else None
        else:
             log_callback("Using original video audio.")
             final_audio_clip = base_clip_layer.audio if base_clip_layer and hasattr(base_clip_layer, 'audio') else None

        # Downscale for performance
        if base_clip_layer and base_clip_layer.size and base_clip_layer.size[1] > 720:
            log_callback(f"Downscaling video from {base_clip_layer.size[1]}p to 720p...")
            base_clip_layer = base_clip_layer.resize(height=720)
        media_size = base_clip_layer.size if base_clip_layer else (1280, 720)
        log_callback(f"Karaoke: Video media size set to {media_size}")

    else: # Audio input
        log_callback("Karaoke: Processing AUDIO input.")
        try:
            if audio_path_override and os.path.exists(audio_path_override):
                 log_callback(f"Using override audio: {os.path.basename(audio_path_override)}")
                 final_audio_clip = mp.AudioFileClip(audio_path_override)
            else:
                 log_callback("Using original input audio.")
                 final_audio_clip = mp.AudioFileClip(input_path)

            base_clip_duration = final_audio_clip.duration if final_audio_clip else 0
            if base_clip_duration <= 0:
                 log_callback("Error: Audio clip has zero or negative duration.")
                 return

            media_size = (1280, 720)
            base_clip_layer = mp.ColorClip(size=media_size, color=[0, 0, 0], duration=base_clip_duration)
            log_callback(f"Karaoke: Created COLOR base layer. Size={media_size}, Duration={base_clip_duration:.2f}s")
        except Exception as e:
            log_callback(f"Error loading audio clip or creating base ColorClip: {e}")
            return

    # <<< NOTE: Using previous strategy of collecting tuples and compositing later >>>
    text_clips = [] # Now this will just be the final composite clip for each segment

    log_callback("Creating karaoke text clips...")
    last_segment_end = 0
    for i, seg in enumerate(segments):
         start_time = seg.get('start', last_segment_end)
         end_time = seg.get('end', start_time + 2)

         start_time = max(0, min(start_time, base_clip_duration))
         end_time = max(start_time, min(end_time, base_clip_duration))
         seg['start'] = start_time
         seg['end'] = end_time

         duration = end_time - start_time
         if duration <= 0.01:
              log_callback(f"Skipping segment with near-zero duration after capping: {seg.get('text','')[::30]}...")
              continue

         # create_karaoke_clip now returns the FINAL composite clip for the segment
         clip = create_karaoke_clip(seg, media_size, is_video_input, log_callback)

         if clip:
             log_callback(f"Karaoke: Adding final clip - Start={clip.start:.2f}s, Duration={clip.duration:.2f}s, Size={clip.size}, Pos={clip.pos}")
             # Ensure duration does not exceed video length AFTER setting start time
             adjusted_duration = min(clip.duration, base_clip_duration - clip.start)
             if adjusted_duration > 0.01:
                 clip = clip.set_duration(adjusted_duration)
                 text_clips.append(clip)
             else:
                  log_callback(f"Karaoke: Clip duration became zero after trimming for '{seg.get('text', '')[:30]}...'")
                  if hasattr(clip, 'close'): clip.close()
         else:
              log_callback(f"Karaoke: create_karaoke_clip returned None for segment {i}")
         last_segment_end = end_time


    if not text_clips:
         log_callback("Warning: No valid karaoke clips were generated.")
         if base_clip_layer is None:
              log_callback("Error: Base layer clip not defined.")
              return
         final_clip = base_clip_layer
    else:
        log_callback(f"Final Karaoke Composite: Base LAYER type={type(base_clip_layer).__name__}, Size={base_clip_layer.size if base_clip_layer else 'None'}, Duration={base_clip_duration:.2f}, Num text clips={len(text_clips)}")
        if base_clip_layer is None:
             log_callback("Error: Base layer clip is None before final compositing.")
             return
        # <<< FIX: Composite base layer + final text clips >>>
        final_clip = mp.CompositeVideoClip(
            [base_clip_layer] + text_clips, # Just base layer and final segment composites
            size=base_clip_layer.size,
            use_bgclip=True
        ).set_duration(base_clip_duration)

    if final_audio_clip:
        try:
            audio_dur = final_audio_clip.duration if final_audio_clip and final_audio_clip.duration is not None else 0
            clip_dur = final_clip.duration if final_clip and final_clip.duration is not None else 0
            safe_duration = min(audio_dur, clip_dur)

            if safe_duration > 0:
                safe_audio = final_audio_clip.subclip(0, safe_duration)
                final_clip = final_clip.set_audio(safe_audio)
                log_callback(f"Set final audio duration to {final_clip.audio.duration:.2f}s (matching video duration {final_clip.duration:.2f}s)")
            else:
                 log_callback("Warning: Calculated safe audio duration is zero or less.")
                 final_clip = final_clip.set_audio(None)
        except Exception as audio_err:
             log_callback(f"Warning: Could not set final audio clip: {audio_err}")
             final_clip = final_clip.set_audio(None)
    else:
        log_callback("Warning: No audio track available for final video.")
        final_clip = final_clip.set_audio(None)

    # Write the final video file
    try:
        log_callback("Writing final karaoke video file... (Using hardware acceleration, may be slow)")
        final_clip.write_videofile(
            output_filename, codec="h264_videotoolbox", audio_codec="aac", fps=24,
            temp_audiofile='temp-audio.m4a', remove_temp=True, preset="fast", threads=8, logger='bar'
        )
        log_callback(f"Success! Karaoke video successfully generated: '{output_filename}'")
    except Exception as e:
        log_callback(f"Hardware acceleration failed: {e}")
        log_callback("Trying again with software encoder (this will be much slower)...")
        final_clip.write_videofile(
            output_filename, codec="libx264", audio_codec="aac", fps=24,
            temp_audiofile='temp-audio.m4a', remove_temp=True, preset="fast",
            threads=8, logger='bar'
        )
        log_callback(f"Success! Karaoke video successfully generated: '{output_filename}'")
    finally:
        # Close clips
        if 'base_clip_layer' in locals() and base_clip_layer and hasattr(base_clip_layer, 'close'): base_clip_layer.close()
        if 'final_audio_clip' in locals() and final_audio_clip and hasattr(final_audio_clip, 'close'): final_audio_clip.close()
        if 'final_clip' in locals() and final_clip and hasattr(final_clip, 'close'): final_clip.close()
        # Close individual text clips (which are now composites)
        for clip in text_clips:
            if hasattr(clip, 'close'): clip.close()

