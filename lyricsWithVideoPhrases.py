import os
import argparse
from pydub import AudioSegment # type: ignore
import whisper # type: ignore
import moviepy.editor as mp # type: ignore

# --- Configuration ---
WHISPER_MODEL = "small.en"
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv']
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.flac']

def extract_audio(input_path, wav_path="temp_audio.wav"):
    """
    Extracts audio from any video/audio file and saves it as a temporary WAV file.
    pydub uses FFmpeg in the background to handle various formats.
    """
    try:
        print(f"Extracting audio from '{os.path.basename(input_path)}'...")
        audio = AudioSegment.from_file(input_path)
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
    Generates a lyrics video. Overlays subtitles on the original video if the
    input was a video, otherwise creates lyrics on a black background.
    """
    if not segments:
        print("No segments to process. Skipping video generation.")
        return

    print("Starting video generation...")
    # Load the original media to get duration and audio
    original_media = mp.VideoFileClip(input_path) if is_video_input else mp.AudioFileClip(input_path)
    
    text_clips = []
    for seg in segments:
        start_time = seg['start']
        end_time = seg['end']
        text = seg['text'].strip()
        duration = end_time - start_time

        if duration <= 0 or not text:
            continue

        # Create a styled TextClip for the segment
        txt_clip = mp.TextClip(
            text,
            fontsize=25,
            color='white',
            font='Arial-Bold',
            bg_color='rgba(0, 0, 0, 0.7)',  # Semi-transparent black background
            size=(original_media.w * 0.9, None),
            method='caption'
        ).set_duration(duration).set_start(start_time).set_position(('center', 'bottom'))
        
        text_clips.append(txt_clip)

    if is_video_input:
        # Overlay text on the original video
        base_clip = original_media
        print("Overlaying subtitles on original video.")
    else:
        # Create a black background for audio-only inputs
        base_clip = mp.ColorClip(
            size=(1280, 720),
            color=[0, 0, 0],
            duration=original_media.duration
        )
        print("Creating lyrics video on a black background.")

    # Composite the base clip (video or black screen) with all text clips
    final_clip = mp.CompositeVideoClip([base_clip] + text_clips)
    
    # Set the audio from the original source
    final_clip = final_clip.set_audio(original_media.audio)

    # Write the final video file
    try:
        final_clip.write_videofile(
            output_filename,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=24,
            verbose=False,
            logger=None
        )
        print(f"Lyrics video successfully generated: '{output_filename}'")
    except Exception as e:
        print(f"An error occurred during video writing: {e}")
        print("This might be due to a missing ImageMagick dependency for moviepy.")

def main():
    parser = argparse.ArgumentParser(description="Generate a lyrics video from an audio or video file.")
    parser.add_argument("input_file", help="Path to the input video or audio file.")
    parser.add_argument("-o", "--output_file", help="Path to the output video file.", default=None)
    parser.add_argument("-m", "--model", help="Whisper model to use.", default=WHISPER_MODEL)
    args = parser.parse_args()

    input_path = args.input_file
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at '{input_path}'")
        return

    # Determine if input is video or audio
    file_ext = os.path.splitext(input_path)[1].lower()
    is_video = file_ext in VIDEO_EXTENSIONS

    # Define a default output filename if not provided
    output_path = args.output_file
    if not output_path:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = f"{base_name}_lyrics.mp4"

    # --- Execution Pipeline ---
    temp_wav_path = extract_audio(input_path)
    
    if temp_wav_path:
        segments = transcribe_audio(temp_wav_path, args.model)
        os.remove(temp_wav_path) # Clean up the temporary file
        print(f"Removed temporary file: '{temp_wav_path}'")

        if segments:
            generate_lyrics_video(input_path, segments, output_path, is_video)

if __name__ == "__main__":
    main()
