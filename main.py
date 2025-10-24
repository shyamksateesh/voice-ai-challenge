import os
import argparse
import config # Import our settings

# Import our custom modules
# <<< FIX: Import separate_vocals
from audio_processing import extract_audio, separate_vocals
from transcription import transcribe_audio
from video_processing import generate_phrase_video, generate_karaoke_video

def main():
    parser = argparse.ArgumentParser(description="Generate a phrase-level lyrics video from an audio or video file.")
    parser.add_argument("input_file", help="Path to the input video or audio file.")
    parser.add_argument("-o", "--output_file", help="Path to the output video file.", default=None)
    parser.add_argument("-m", "--model", help="Whisper model to use.", default=config.WHISPER_MODEL)
    
    parser.add_argument("--wipe-text", action="store_true", help="Use karaoke wipe effect (slow)")
    # <<< FIX: Un-comment the separate-audio argument
    parser.add_argument("--separate-vocals", action="store_true", help="Separate vocals before transcription (very slow)")
    
    args = parser.parse_args()

    input_path = args.input_file
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at '{input_path}'")
        return

    file_ext = os.path.splitext(input_path)[1].lower()
    is_video = file_ext in config.VIDEO_EXTENSIONS

    output_path = args.output_file
    if not output_path:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = f"{base_name}_lyrics.mp4"

    temp_wav_path = config.TEMP_WAV_FILE
    # <<< FIX: Add a variable for the final vocal path
    vocals_wav_path = config.VOCALS_WAV_FILE
    # This will be the path we send to Whisper
    transcription_input_path = temp_wav_path
    # <<< FIX: Add a flag to track if separation worked
    vocal_separation_succeeded = False
    
    try:
        # --- Step 1: Extract Audio ---
        if not extract_audio(input_path, temp_wav_path):
            print("Failed to extract audio. Exiting.")
            return
        
        # --- Step 1b: Source Separation (if flagged) ---
        if args.separate_vocals:
            if separate_vocals(temp_wav_path, vocals_wav_path):
                # Success! Update the path for Whisper
                transcription_input_path = vocals_wav_path
                vocal_separation_succeeded = True # <<< FIX: Set the flag
            else:
                print("Vocal separation failed. Proceeding with original audio.")
                # transcription_input_path remains temp_wav_path
        
        # --- Step 2: Transcribe ---
        # <<< FIX: Use the (potentially new) transcription_input_path
        segments = transcribe_audio(transcription_input_path, args.model, word_timestamps=args.wipe_text)
        
        # --- Step 3: Generate Video ---
        if segments:
            if args.wipe_text:
                print("Wipe text selected. Starting karaoke video generation (this is slow)...")
                # <<< FIX: Pass the flag
                generate_karaoke_video(input_path, segments, output_path, is_video, vocal_separation_succeeded)
            else:
                print("Starting phrase video generation...")
                # <<< FIX: Pass the flag
                generate_phrase_video(input_path, segments, output_path, is_video, vocal_separation_succeeded)
        else:
            print("No segments transcribed, nothing to render.")
    
    finally:
        # --- Step 4: Cleanup ---
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
            print(f"Removed temporary file: '{temp_wav_path}'")
        # <<< FIX: Add cleanup for the new vocals file
        if os.path.exists(vocals_wav_path):
            os.remove(vocals_wav_path)
            print(f"Removed temporary file: '{vocals_wav_path}'")

if __name__ == "__main__":
    main()


