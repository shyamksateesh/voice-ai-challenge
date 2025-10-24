import os
import argparse
from pydub import AudioSegment
import whisper
import moviepy.editor as mp
import numpy as np

# --- Config ---
WHISPER_MODEL = "small.en"
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv']
FONT_SIZE = 48
TEXT_COLOR = "white"
BG_COLOR = "gray30"
SUBTITLE_Y = 0.85


def extract_audio(input_path, wav_path="temp_audio.wav"):
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
    try:
        print(f"Loading Whisper model '{model_name}'...")
        model = whisper.load_model(model_name)
        result = model.transcribe(wav_path, language='en', fp16=False, word_timestamps=True)
        return result.get("segments", [])
    except Exception as e:
        print(f"Error during transcription: {e}")
        return []


def create_karaoke_clip(segment, media_size):
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
            fontsize=FONT_SIZE,
            color=BG_COLOR,
            method="label",
        )
        .set_position(("center", media_size[1] * SUBTITLE_Y))
        .set_duration(seg_duration)
        .set_start(seg_start)
    )

    # Highlighted text (foreground)
    highlight_clip = (
        mp.TextClip(
            phrase,
            fontsize=FONT_SIZE,
            color=TEXT_COLOR,
            method="label",
        )
        .set_position(("center", media_size[1] * SUBTITLE_Y))
        .set_duration(seg_duration)
        .set_start(seg_start)
    )

    if not words:
        # Fallback if no word-level timestamps
        return highlight_clip

    # Generate word timing map for smooth wipe
    total_chars = len(phrase)
    char_time_map = np.zeros(total_chars)
    idx = 0
    for w in words:
        word_text = w.get("text", "")
        w_start, w_end = w.get("start"), w.get("end")
        if w_start is None or w_end is None:
            continue
        for c in range(len(word_text)):
            if idx + c < total_chars:
                char_time_map[idx + c] = w_start + (c / len(word_text)) * (w_end - w_start)
        idx += len(word_text) + 1  # +1 for space

    # Animation mask: reveals text gradually based on time
    def make_frame(t):
        width = int(base_clip.size[0] * (t / seg_duration))
        width = np.clip(width, 0, base_clip.size[0])
        mask = np.zeros((base_clip.size[1], base_clip.size[0]))
        mask[:, :width] = 255
        return mask

    mask_clip = mp.VideoClip(make_frame, duration=seg_duration, ismask=True)
    highlight_clip = highlight_clip.set_mask(mask_clip)

    return mp.CompositeVideoClip([base_clip, highlight_clip], size=media_size)


def generate_lyrics_video(input_path, segments, output_filename, is_video_input):
    if not segments:
        print("No transcription segments found.")
        return

    print("Generating karaoke video...")

    if is_video_input:
        base_clip = mp.VideoFileClip(input_path)
        media_size = base_clip.size
    else:
        audio_clip = mp.AudioFileClip(input_path)
        media_size = (1280, 720)
        base_clip = mp.ColorClip(media_size, color=[0, 0, 0], duration=audio_clip.duration).set_audio(audio_clip)

    text_clips = []
    for seg in segments:
        clip = create_karaoke_clip(seg, media_size)
        if clip:
            text_clips.append(clip)

    final_clip = mp.CompositeVideoClip([base_clip] + text_clips)
    if is_video_input:
        final_clip = final_clip.set_audio(base_clip.audio)

    final_clip.write_videofile(
        output_filename,
        codec="libx264",
        audio_codec="aac",
        fps=20, #
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
        preset="ultrafast", #
        verbose=False,
        logger='bar',
    )

    print(f"\n✅ Karaoke video created: {output_filename}")


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

    is_video = os.path.splitext(input_path)[1].lower() in VIDEO_EXTENSIONS
    output_path = args.output_file or f"{os.path.splitext(os.path.basename(input_path))[0]}_karaoke.mp4"

    wav_path = extract_audio(input_path)
    if not wav_path:
        print("Failed to extract audio.")
        return

    segments = transcribe_audio(wav_path, args.model)
    os.remove(wav_path)

    if segments:
        generate_lyrics_video(input_path, segments, output_path, is_video)
    else:
        print("No segments transcribed.")


if __name__ == "__main__":
    main()
