import os
import argparse
from pydub import AudioSegment # type: ignore
import whisper # type: ignore
import moviepy.editor as mp # type: ignore

# --- Configuration ---
#WHISPER_MODEL = "small.en"
WHISPER_MODEL = "medium.en"
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv']
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', 'flac']

# --- Subtitle Style ---
# FONT_SIZE is now dynamic, calculated as a percentage of video width
RELATIVE_FONT_SIZE = 0.045 # <<< FIX: 4.5% of video width. (Was FONT_SIZE = 48)
FONT_COLOR = 'white'
FONT_FAMILY = 'Arial-Bold'
FONT_BACKGROUND = 'rgba(0, 0, 0, 0.6)' # Semi-transparent black
SUBTITLE_Y_POSITION = 0.85 # 85% from the top

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
        print(f"Temporary WAV file created at '{wav_path}'.")
        return wav_path
    except Exception as e:
        print(f"Error during audio extraction: {e}")
        return None

def transcribe_audio(wav_path, model_name):
    """Transcribes a WAV file using Whisper and returns phrase-level segments."""
    try:
        print(f"Loading Whisper model '{model_name}'...")
        model = whisper.load_model(model_name)
        print("Starting transcription...")
        result = model.transcribe(wav_path, language='en', fp16=False)
        
        segments = result.get('segments', [])
        print(f"Transcription complete. Found {len(segments)} segments.")
        return segments
    except Exception as e:
        print(f"An error occurred during transcription: {e}")
        return []

def generate_lyrics_video(input_path, segments, output_filename, is_video_input):
    """
    Generates a lyrics video with polished, readable, phrase-level subtitles
    that dynamically resize and do NOT overlap.
    """
    if not segments:
        print("No segments to process. Skipping video generation.")
        return

    print("Starting video generation...")
    # Load the original media to get duration and audio
    if is_video_input:
        base_clip = mp.VideoFileClip(input_path)
        
        # --- FIX: Downscale video to 720p for faster, consistent rendering ---
        if base_clip.size[1] > 720: # if height is greater than 720p
            print(f"Downscaling video from {base_clip.size[1]}p to 720p...")
            base_clip = base_clip.resize(height=720) # Resize, keeping aspect ratio
        
        media_size = base_clip.size
    else:
        # Audio-only is already capped at our default
        audio_clip = mp.AudioFileClip(input_path)
        media_size = (1280, 720) # Default to 720p for audio-only
        base_clip = mp.ColorClip(
            size=media_size,
            color=[0, 0, 0],
            duration=audio_clip.duration
        ).set_audio(audio_clip)
    
    # --- Calculate dynamic font size based on video width ---
    dynamic_font_size = int(media_size[0] * RELATIVE_FONT_SIZE)
    print(f"Video width: {media_size[0]}px. Setting font size to {dynamic_font_size}px.")
    
    text_clips = []
    
    # Iterate with an index to look ahead
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
            color=FONT_COLOR,
            font=FONT_FAMILY,
            bg_color=FONT_BACKGROUND, 
            size=(media_size[0] * 0.9, None), # 90% width
            method='caption'
        ).set_duration(duration).set_start(start_time).set_position(('center', SUBTITLE_Y_POSITION), relative=True)
        
        text_clips.append(txt_clip)

    final_clip = mp.CompositeVideoClip([base_clip] + text_clips)
    
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
    parser = argparse.ArgumentParser(description="Generate a phrase-level lyrics video from an audio or video file.")
    parser.add_argument("input_file", help="Path to the input video or audio file.")
    parser.add_argument("-o", "--output_file", help="Path to the output video file.", default=None)
    parser.add_argument("-m", "--model", help="Whisper model to use.", default=WHISPER_MODEL)
    args = parser.parse_args()

    input_path = args.input_file
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at '{input_path}'")
        return

    file_ext = os.path.splitext(input_path)[1].lower()
    is_video = file_ext in VIDEO_EXTENSIONS

    output_path = args.output_file
    if not output_path:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = f"{base_name}_lyrics.mp4"

    temp_wav_path = "temp_audio.wav"
    wav_path = None
    
    try:
        wav_path = extract_audio(input_path, temp_wav_path)
        
        if wav_path:
            segments = transcribe_audio(wav_path, args.model)
            if segments:
                generate_lyrics_video(input_path, segments, output_path, is_video)
            else:
                print("No segments transcribed, nothing to render.")
    
    finally:
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
            print(f"Removed temporary file: '{temp_wav_path}'")

if __name__ == "__main__":
    main()