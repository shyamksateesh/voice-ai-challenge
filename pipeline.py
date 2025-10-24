import os
import config 
from audio_processing import extract_audio, separate_vocals
from transcription import transcribe_audio
from video_processing import generate_phrase_video, generate_karaoke_video

# This is our main "worker" function that the server will call in a thread
def run_pipeline(input_file_path, output_file_name, options):
    """
    Runs the entire video generation pipeline.
    'options' is a dictionary:
    {
        "model": "medium.en",
        "wipe_text": True,
        "separate_vocals": False,
        "is_video": True
    }
    """
    
    # --- Setup Temporary File Paths ---
    # We use the paths from the config file
    temp_wav_path = config.TEMP_WAV_FILE
    vocals_wav_path = config.VOCALS_WAV_FILE
    transcription_input_path = temp_wav_path # Default to the original extracted audio
    vocal_separation_succeeded = False

    output_file_path = os.path.join("outputs", output_file_name)

    try:
        # --- Step 1: Extract Audio ---
        if not extract_audio(input_file_path, temp_wav_path):
            raise Exception("Failed to extract audio.")
        
        # --- Step 1b: Source Separation (if flagged) ---
        if options.get("separate_vocals"):
            print("Vocal separation selected. Starting...")
            if separate_vocals(temp_wav_path, vocals_wav_path):
                print("Vocal separation successful. Transcribing vocals only.")
                transcription_input_path = vocals_wav_path
                vocal_separation_succeeded = True
            else:
                # This is your robust error handling from before
                print("Vocal separation failed. Proceeding with original audio.")
        
        # --- Step 2: Transcribe ---
        print(f"Starting transcription... (File: {transcription_input_path})")
        segments = transcribe_audio(
            transcription_input_path, 
            options.get("model", "small.en"), 
            options.get("wipe_text", False) # Pass word_timestamp request
        )

        if not segments:
            raise Exception("No segments transcribed, nothing to render.")

        # --- Step 3: Generate Video ---
        if options.get("wipe_text"):
            # Karaoke "Wipe Text" generation
            print("Wipe text selected. Starting karaoke video generation (this is slow)...")
            generate_karaoke_video(
                input_file_path, 
                segments, 
                output_file_path, 
                options.get("is_video", True),
                vocal_separation_succeeded
            )
        else:
            # Standard "Phrase" generation
            print("Starting phrase video generation...")
            generate_phrase_video(
                input_file_path, 
                segments, 
                output_file_path, 
                options.get("is_video", True),
                vocal_separation_succeeded
            )
        
        print(f"Pipeline complete. Final file at: {output_file_path}")
        return output_file_path # Return the path for the download link

    except Exception as e:
        print(f"--- PIPELINE FAILED ---")
        print(str(e))
        raise e # Re-raise the exception so the server knows it failed
    
    finally:
        # --- Cleanup ---
        print("Cleaning up temporary audio files...")
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
        if os.path.exists(vocals_wav_path):
            os.remove(vocals_wav_path)
