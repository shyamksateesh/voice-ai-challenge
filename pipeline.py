import os
import config
from audio_processing import extract_audio, separate_vocals
from transcription import transcribe_audio
from video_processing import generate_phrase_video, generate_karaoke_video

def run_pipeline(input_path, output_path, options, log_callback):
    """
    Runs the full media processing pipeline.
    
    Args:
        input_path (str): Path to the uploaded media file.
        output_path (str): Path to save the final video.
        options (dict): A dictionary of user-selected options including 'is_video'.
        log_callback (function): A function to call with log messages.
    """
    
    # --- 1. Get file type from options ---
    log_callback("Determining file type...")
    # <<< FIX: Get is_video directly from the options dict passed by app.py
    is_video = options.get("is_video", False) 
    log_callback(f"File type identified as: {'Video' if is_video else 'Audio'}")

    temp_wav_path = os.path.join(config.UPLOADS_DIR, "temp_audio.wav")
    vocal_track_path = None
    
    try:
        # --- 2. Extract Audio ---
        log_callback("Extracting base audio track...")
        base_audio_path = extract_audio(input_path, temp_wav_path, log_callback)
        if not base_audio_path:
            raise Exception("Failed to extract audio.")
        
        # --- 3. (Optional) Separate Vocals ---
        if options.get("do_separate_vocals"):
            log_callback("Vocal separation selected. This will be slow...")
            vocal_track_path = separate_vocals(base_audio_path, log_callback)
            if vocal_track_path:
                log_callback("Vocal separation successful. Transcribing vocals only.")
                audio_to_transcribe = vocal_track_path
            else:
                log_callback("Vocal separation failed. Transcribing original audio.")
                audio_to_transcribe = base_audio_path
        else:
            log_callback("Skipping vocal separation.")
            audio_to_transcribe = base_audio_path

        # --- 4. Transcribe Audio ---
        log_callback(f"Starting transcription with '{options.get('model_size')}' model...")
        segments = transcribe_audio(
            audio_to_transcribe,
            options.get("model_size"),
            options.get("do_wipe_text"), 
            log_callback
        )
        if not segments:
            raise Exception("Transcription failed or produced no segments.")
        log_callback(f"Transcription complete. Found {len(segments)} segments.")

        # --- 5. Generate Video ---
        if options.get("do_wipe_text"):
            log_callback("Wipe text selected. Starting karaoke video generation (this is slow)...")
            generate_karaoke_video(
                input_path=input_path,
                segments=segments,
                output_filename=output_path,
                is_video_input=is_video, # <<< Pass the correct flag
                vocal_track_path=vocal_track_path, 
                log_callback=log_callback
            )
        else:
            log_callback("Starting phrase video generation...")
            generate_phrase_video(
                input_path=input_path,
                segments=segments,
                output_filename=output_path,
                is_video_input=is_video, # <<< Pass the correct flag
                vocal_track_path=vocal_track_path, 
                log_callback=log_callback
            )
        
        log_callback("Video generation complete.")

    finally:
        # --- 6. Clean up temporary files ---
        log_callback("Cleaning up temporary files...")
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
        if vocal_track_path and os.path.exists(vocal_track_path):
            os.remove(vocal_track_path)
        log_callback("Cleanup complete.")