import os
import argparse
from pydub import AudioSegment
import whisper
import moviepy.editor as mp
import numpy as np

# --- Config ---
WHISPER_MODEL = "medium.en" # <<< Set to medium
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv']

# --- Style Config ---
RELATIVE_FONT_SIZE = 0.045 # <<< Dynamic font size (4.5% of width)
KARAOKE_FONT = "Courier-Bold" # <<< Monospace font is needed for wipe
TEXT_COLOR = "white"
BG_COLOR = "gray30"
SUBTITLE_Y_POSITION = 0.85


def extract_audio(input_path, wav_path="temp_audio.wav"):
    """
    Extracts audio, standardizes it to 16kHz mono for Whisper,
    and saves it as a temporary WAV file.
    """
    try:
        print(f"Extracting audio from '{os.path.basename(input_path)}'...")
        audio = AudioSegment.from_file(input_path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(wav_path, format="wav")
        return wav_path
    except Exception as e:
        print(f"Error during audio extraction: {e}")
        return None


def transcribe_audio(wav_path, model_name):
    """
    Transcribes the audio file using Whisper and requests word-level timestamps.
    """
    try:
        print(f"Loading Whisper model '{model_name}'...")
        model = whisper.load_model(model_name)
        result = model.transcribe(wav_path, language='en', fp16=False, word_timestamps=True)
        print("Transcription complete.")
        return result.get("segments", [])
    except Exception as e:
        print(f"Error during transcription: {e}")
        return []


# <<< FIX: Function now accepts dynamic_font_size
def create_karaoke_clip(segment, media_size, dynamic_font_size):
    """Creates a single text clip with a left-to-right highlighting animation."""
    seg_start = max(0, segment.get("start", 0))
    seg_end = segment.get("end", seg_start + 2)
    seg_duration = max(0.5, seg_end - seg_start)
    phrase = segment.get("text", "").strip()
    words = segment.get("words", [])

    if not phrase:
        return None

    # Create base text (unhighlighted background)
    base_clip = (
        mp.TextClip(
            phrase,
            fontsize=dynamic_font_size, # <<< FIX: Use dynamic size
            color=BG_COLOR,
            font=KARAOKE_FONT,
            method="caption", # <<< FIX: Use caption for robust sizing
            size=(media_size[0] * 0.9, None)
        )
        .set_position(("center", media_size[1] * SUBTITLE_Y_POSITION))
        .set_duration(seg_duration)
        .set_start(seg_start)
    )

    # Highlighted text (foreground)
    highlight_clip = (
        mp.TextClip(
            phrase,
            fontsize=dynamic_font_size, # <<< FIX: Use dynamic size
            color=TEXT_COLOR,
            font=KARAOKE_FONT,
            method="caption", # <<< FIX: Use caption for robust sizing
            size=(media_size[0] * 0.9, None)
        )
        .set_position(("center", media_size[1] * SUBTITLE_Y_POSITION))
        .set_duration(seg_duration)
        .set_start(seg_start)
    )

    if not words:
        # Fallback if no word-level timestamps
        return highlight_clip

    # --- This is the original GPT wipe logic (preserved as requested) ---
    total_chars = len(phrase)
    char_time_map = np.zeros(total_chars)
    idx = 0
    for w in words:
        word_text = w.get("text", "")
        w_start, w_end = w.get("start"), w.get("end")
        if w_start is None or w_end is None:
            continue
        
        # This logic is flawed, but preserved per request
        word_len = len(word_text)
        if word_len > 0:
            for c in range(word_len):
                if idx + c < total_chars:
                    char_time_map[idx + c] = w_start + (c / word_len) * (w_end - w_start)
        idx += word_len + 1  # +1 for space

    # Animation mask: reveals text gradually based on time
    def make_frame(t):
        # This is a simple linear wipe, not based on the char_time_map
        # (This was the bug in the original GPT code, preserved here)
        width = int(base_clip.size[0] * (t / seg_duration))
        width = np.clip(width, 0, base_clip.size[0])
        mask = np.zeros((base_clip.size[1], base_clip.size[0]), dtype=np.uint8)
        mask[:, :width] = 255
        return mask
    # --- End of original wipe logic ---

    mask_clip = mp.VideoClip(make_frame, duration=seg_duration, ismask=True)
    highlight_clip = highlight_clip.set_mask(mask_clip)

    return mp.CompositeVideoClip([base_clip, highlight_clip], size=media_size)


def generate_lyrics_video(input_path, segments, output_filename, is_video_input):
    """
    Generates a lyrics video, capping quality at 720p for speed.
    """
    if not segments:
        print("No transcription segments found.")
        return

    print("Generating karaoke video...")

    if is_video_input:
        base_clip = mp.VideoFileClip(input_path)
        
        # --- FIX: Downscale video to 720p for faster, consistent rendering ---
        if base_clip.size[1] > 720: # if height is greater than 720p
            print(f"Downscaling video from {base_clip.size[1]}p to 720p...")
            base_clip = base_clip.resize(height=720) # Resize, keeping aspect ratio
        
        media_size = base_clip.size
    else:
        audio_clip = mp.AudioFileClip(input_path)
        media_size = (1280, 720)
        base_clip = mp.ColorClip(media_size, color=[0, 0, 0], duration=audio_clip.duration).set_audio(audio_clip)

    # --- FIX: Calculate dynamic font size ---
    dynamic_font_size = int(media_size[0] * RELATIVE_FONT_SIZE)
    print(f"Video width: {media_size[0]}px. Setting font size to {dynamic_font_size}px.")

    text_clips = []
    for seg in segments:
        # <<< FIX: Pass dynamic font size to clip creator
        clip = create_karaoke_clip(seg, media_size, dynamic_font_size)
        if clip:
            text_clips.append(clip)

    final_clip = mp.CompositeVideoClip([base_clip] + text_clips)
    if is_video_input:
        final_clip = final_clip.set_audio(base_clip.audio)

    # --- FIX: Write final video with hardware acceleration ---
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
            logger='bar' # Show a progress bar
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


def main():
    parser = argparse.ArgumentParser(description="Generate karaoke-style lyrics video using Whisper.")
    parser.add_argument("input_file", help="Input video or audio file path.")
    parser.add_argument("-o", "--output_file", help="Output file path.", default=None)
    parser.add_argument("-m", "--model", help="Whisper model to use.", default=WHISPER_MODEL)
    args = parser.parse_args()

    input_path = args.input_file
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    # --- FIX: Use os.path.splitext ---
    is_video = os.path.splitext(input_path)[1].lower() in VIDEO_EXTENSIONS
    output_path = args.output_file or f"{os.path.splitext(os.path.basename(input_path))[0]}_karaoke.mp4"

    wav_path = "temp_audio.wav"
    try:
        wav_path_result = extract_audio(input_path, wav_path)
        if not wav_path_result:
            print("Failed to extract audio.")
            return

        segments = transcribe_audio(wav_path, args.model)
        
        if segments:
            generate_lyrics_video(input_path, segments, output_path, is_video)
        else:
            print("No segments transcribed.")
            
    finally:
        # Ensure temp file is always cleaned up
        if os.path.exists(wav_path):
            os.remove(wav_path)
            print(f"Removed temporary file: '{wav_path}'")


if __name__ == "__main__":
    main()