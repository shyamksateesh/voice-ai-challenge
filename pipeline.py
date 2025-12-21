import os
import time
import config # Import config settings
from audio_processing import extract_audio, separate_vocals # Import audio functions
from transcription import transcribe_audio, perform_forced_alignment # Import transcription functions
from video_processing import generate_phrase_video, generate_karaoke_video # Import video functions

def run_pipeline(input_path, output_path, options, log_callback=print):
    """
    Runs the full processing pipeline: audio extraction, optional separation,
    transcription, optional alignment, and video generation.
    Returns the transcript segments for further use.
    """
    start_time = time.time()
    log_callback("Starting main processing pipeline...")

    # --- Options ---
    model_name = options.get('model', config.WHISPER_MODEL)
    do_separate_vocals = options.get('do_separate_vocals', False)
    do_wipe_text = options.get('do_wipe_text', False)
    # <<< FIX: Receive is_video directly from options >>>
    is_video = options.get('is_video', False)
    log_callback(f"Input type determined as: {'Video' if is_video else 'Audio'}")

    temp_wav_path = "uploads/temp_audio.wav" # Define temp path
    vocals_only_path = None # Path for separated vocals if created
    final_audio_for_video = None # Path for audio to use in final video

    try:
        # --- 1. Audio Extraction ---
        log_callback("Extracting base audio track...")
        extracted_wav_path = extract_audio(input_path, temp_wav_path, log_callback)
        if not extracted_wav_path:
            raise ValueError("Audio extraction failed.")
        
        # Default audio path is the extracted one
        audio_path_for_transcription = extracted_wav_path
        final_audio_for_video = input_path if is_video else extracted_wav_path # Default final audio


        # --- 2. Optional Vocal Separation ---
        if do_separate_vocals:
            log_callback("Vocal separation selected.")
            vocals_only_path_result = separate_vocals(extracted_wav_path, log_callback)
            if vocals_only_path_result:
                audio_path_for_transcription = vocals_only_path_result # Transcribe vocals only
                vocals_only_path = vocals_only_path_result # Keep track for cleanup
                if config.REPLACE_AUDIO_WITH_VOCALS:
                     final_audio_for_video = vocals_only_path_result # Use vocals in final video
                     log_callback("Using separated vocal track for final video audio.")
                else:
                     log_callback("Using original audio for final video (vocals used for transcription only).")

            else:
                log_callback("Vocal separation failed. Proceeding with original audio for transcription.")
                # Keep audio_path_for_transcription as extracted_wav_path
        else:
            log_callback("Skipping vocal separation.")


        # --- 3. Transcription ---
        log_callback(f"Starting transcription with '{model_name}' model...")
        segments = transcribe_audio(
             audio_path_for_transcription,
             model_name,
             log_callback,
             # Only request word timestamps if doing wipe text
             word_timestamps_needed = do_wipe_text
        )
        if not segments:
             raise ValueError("Transcription failed or produced no segments.")
             
        # Detect language (needed for alignment)
        detected_language = segments[0].get('language', 'en') # Default to English


        # --- 4. Optional Forced Alignment ---
        if do_wipe_text:
             log_callback("Wipe text selected. Performing forced alignment...")
             # Use the same audio path that was used for transcription
             aligned_segments = perform_forced_alignment(audio_path_for_transcription, segments, detected_language, log_callback)
             if aligned_segments:
                  segments = aligned_segments # Use aligned segments if successful
             else:
                  log_callback("Forced alignment failed. Proceeding with original Whisper timestamps for wipe text (may be inaccurate).")
                  # Keep original segments (which might have basic word timestamps if transcribe_audio provided them)
        else:
            log_callback("Skipping forced alignment.")


        # --- 5. Video Generation ---
        log_callback("Preparing video generation...")
        
        # <<< FIX: Correctly check do_wipe_text option >>>
        if do_wipe_text:
            log_callback("Starting karaoke video generation (word-by-word)...")
            generate_karaoke_video(
                input_path=input_path, # Pass original input for video base
                segments=segments,
                output_filename=output_path,
                is_video_input=is_video, # <<< Pass the correct flag
                log_callback=log_callback,
                audio_path_override=final_audio_for_video # Pass potentially separated audio
            )
        else:
            log_callback("Starting phrase video generation...")
            generate_phrase_video(
                input_path=input_path, # Pass original input for video base
                segments=segments,
                output_filename=output_path,
                is_video_input=is_video, # <<< Pass the correct flag
                log_callback=log_callback,
                audio_path_override=final_audio_for_video # Pass potentially separated audio
            )

        log_callback("Video generation complete.")

        # Return segments for transcript access
        return segments

    except Exception as e:
        log_callback(f"ERROR in pipeline: {e}")
        # Re-raise the exception so the thread function catches it
        raise
    finally:
        # --- Cleanup ---
        log_callback("Cleaning up temporary files...")
        if os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
                log_callback(f"Removed temporary file: {temp_wav_path}")
            except OSError as e:
                 log_callback(f"Error removing temporary file {temp_wav_path}: {e}")

        # Clean up separated vocals file if it was created
        if vocals_only_path and os.path.exists(vocals_only_path):
             try:
                 os.remove(vocals_only_path)
                 log_callback(f"Removed separated vocals file: {vocals_only_path}")
             except OSError as e:
                  log_callback(f"Error removing separated vocals file {vocals_only_path}: {e}")

        # Clean up Demucs output directory if it exists and is empty
        if do_separate_vocals and os.path.exists(config.DEMUCS_OUTPUT_DIR):
             try:
                 if not os.listdir(config.DEMUCS_OUTPUT_DIR): # Only remove if empty
                     os.rmdir(config.DEMUCS_OUTPUT_DIR)
                     log_callback(f"Removed empty Demucs output directory: {config.DEMUCS_OUTPUT_DIR}")
                 else:
                     # It's safer not to automatically delete if unexpected files remain
                     log_callback(f"Note: Demucs output directory {config.DEMUCS_OUTPUT_DIR} not empty, skipping removal.")
             except OSError as e:
                  log_callback(f"Error removing Demucs output directory {config.DEMUCS_OUTPUT_DIR}: {e}")

        end_time = time.time()
        log_callback(f"Cleanup complete.")
        log_callback(f"Pipeline finished in {end_time - start_time:.2f} seconds.")

