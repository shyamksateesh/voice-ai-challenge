import whisper
import whisperx # For forced alignment
import torch # For checking device

# --- Transcription Function ---
# <<< FIX: Added word_timestamps_needed=False as an argument >>>
def transcribe_audio(wav_path, model_name, log_callback=print, word_timestamps_needed=False):
    """
    Transcribes a WAV file using Whisper. Optionally requests word timestamps
    directly from Whisper if word_timestamps_needed is True.
    """
    try:
        log_callback(f"Loading Whisper model '{model_name}'...")
        # Determine device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        log_callback(f"Whisper model loaded onto {device}.") # Log device
        model = whisper.load_model(model_name, device=device)

        log_callback("Starting transcription...")
        # <<< FIX: Pass word_timestamps=word_timestamps_needed >>>
        result = model.transcribe(wav_path, language='en', fp16=False, word_timestamps=word_timestamps_needed)

        segments = result.get('segments', [])
        log_callback(f"Transcription complete. Found {len(segments)} segments.")
        return segments
    except Exception as e:
        log_callback(f"An error occurred during transcription: {e}")
        return []

# --- Forced Alignment Function ---
def perform_forced_alignment(audio_path, segments, detected_language, log_callback=print):
    """
    Performs forced alignment using WhisperX to get accurate word timestamps.
    """
    if not segments:
        log_callback("Cannot perform alignment: No segments provided.")
        return None

    try:
        log_callback("Starting forced alignment with WhisperX...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        batch_size = 16 # According to WhisperX docs

        # 1. Load Alignment Model & Metadata
        log_callback(f"Loading WhisperX alignment model on {device}...")
        model_a, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
        log_callback("Alignment model loaded.")

        # 2. Align whisper output
        log_callback("Aligning segments...")
        result_aligned = whisperx.align(segments, model_a, metadata, audio_path, device, return_char_alignments=False)
        aligned_segments = result_aligned.get("segments")

        if not aligned_segments:
             log_callback("WhisperX alignment did not return any segments.")
             return None

        # Add word timestamps to the original segments structure if they exist
        # WhisperX modifies the segments list/dict in place, adding 'word_segments' or similar
        # Let's refine the structure slightly to match what create_karaoke_clip expects
        output_segments = []
        for seg in aligned_segments:
            # Ensure the segment has the basic keys expected
            new_seg = {
                 'start': seg.get('start'),
                 'end': seg.get('end'),
                 'text': seg.get('text'),
                 'words': seg.get('words', []) # WhisperX puts word timings under 'words' key
            }
            # Make sure 'word' key exists within each word dict
            if new_seg['words']:
                for word_info in new_seg['words']:
                    if 'word' not in word_info and 'text' in word_info:
                         word_info['word'] = word_info.pop('text') # Rename key if needed
            output_segments.append(new_seg)


        log_callback(f"WhisperX alignment complete.")
        return output_segments # Return segments with added 'words' key

    except ImportError as e:
         log_callback(f"ImportError during WhisperX alignment: {e}. Is whisperx installed correctly?")
         return None
    except Exception as e:
        # Log the full traceback for alignment errors
        import traceback
        tb_str = traceback.format_exc()
        log_callback(f"An error occurred during WhisperX alignment: {e}\nTraceback:\n{tb_str}")
        return None # Return None on failure

