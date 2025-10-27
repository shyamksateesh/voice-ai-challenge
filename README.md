# LyrAssist: A Web-Based AI Transcription & Video Tool

A functional prototype of an AI agent that transcribes audio/video files and renders synchronized subtitles. This project provides a web interface for processing media with configurable AI models on a local server.

## Overview

This project is an AI-powered media processing pipeline wrapped in a Flask web application. It automates the workflow of transcribing audio (from files or live recording) and creating subtitled videos.

A user can upload a video/audio file or record new audio directly in the browser. The backend server (running locally) processes the media using state-of-the-art AI models, optionally separating vocals first. It then composites a new video file with either synchronized phrase-level subtitles or an experimental word-by-word karaoke effect.

This serves as a powerful prototype for accessibility tools (real-time captioning) and creative workflows (lyric video generation).

## Core Features

* **Simple Web UI:** A clean interface to upload media, record new audio, and select processing options.
* **Live Backend Logging:** The UI displays real-time log messages from the backend processing pipeline.
* **Asynchronous Backend:** Uses Flask and background threading to handle long-running tasks (like transcription and video rendering) without timing out the browser.
* **Modular Pipeline:** The backend is refactored into a scalable, multi-file structure (`pipeline.py`, `audio_processing.py`, `transcription.py`, `video_processing.py`).
* **Configurable AI Options:**
    * **Vocal Separation:** Checkbox to enable `demucs` to isolate vocals from music before transcription (improves accuracy).
    * **Whisper Model:** Selectable model size (`tiny`, `base`, `small`, `medium`, `large`) via UI to balance speed and accuracy.
    * **Karaoke Wipe Mode (Experimental):** Checkbox to enable word-by-word highlighting using WhisperX for forced alignment. (Note: Currently under development and may have rendering issues).
* **Dynamic Video Rendering:**
    * **Phrase Mode:** Renders clean, phrase-level subtitles with dynamic font sizing and correct positioning for any video aspect ratio (landscape/portrait).
    * **Audio-Only Mode:** Automatically generates a 720p black-screen video (centered text) for `.mp3` or `.wav` inputs.
    * **Quality Cap:** Input videos are downscaled to 720p during processing for faster, consistent render times.
    * **Hardware Acceleration:** Utilizes `h264_videotoolbox` on macOS for significantly faster video encoding.
    * **Embedded Player:** The final processed video is embedded directly on the page for playback, with a separate download link.

## Tech Stack

* **Backend:** Python, Flask
* **Frontend:** HTML5, Tailwind CSS, JavaScript (MediaRecorder API)
* **AI/ML:** OpenAI Whisper (Transcription), WhisperX (Forced Alignment), Demucs (Vocal Separation)
* **Media Processing:** MoviePy (Video Compositing), Pydub (Audio Handling)
* **Dependencies:** PyTorch, NumPy

## How to Run This Project

### 1. Prerequisites

* Python 3.10+
* FFmpeg (required by `moviepy` and `pydub`)
* (On macOS) `h264_videotoolbox` support in FFmpeg is used for hardware-accelerated video encoding.

### 2. Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/shyamksateesh/voice-ai-challenge.git](https://github.com/shyamksateesh/voice-ai-challenge.git)
    cd voice-ai-challenge
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    *(This may take time as it includes PyTorch, Demucs, and WhisperX)*
    ```bash
    pip install flask pydub openai-whisper moviepy numpy demucs torch torchaudio "numpy<2" --force-reinstall
    pip install git+[https://github.com/m-bain/whisperX.git](https://github.com/m-bain/whisperX.git) --upgrade
    ```
    *Note: Downgrading NumPy is currently necessary due to compatibility issues between WhisperX dependencies and NumPy 2.x.*

4.  **Create required folders:**
    The application needs these folders to function.
    ```bash
    mkdir uploads
    mkdir outputs
    touch uploads/.gitkeep outputs/.gitkeep # Optional: to keep folders in git
    ```

### 3. Running the Application

1.  **Run the Flask server:**
    ```bash
    python app.py
    ```

2.  **Open the application in your browser:**
    Navigate to `http://127.0.0.1:5001` (or the port specified in your terminal).

3.  **Use the UI:**
    * Select a video/audio file or record audio.
    * Choose your processing options (Whisper model, vocal separation, karaoke mode).
    * Click "Start Processing" and monitor the live logs and progress bar.

## Future Work (Roadmap)

This prototype is the foundation for a more robust, real-time application.

* **Refine Karaoke Rendering:** Debug and stabilize the multi-line word-wipe effect.
* **Real-Time Streaming:** Implement a WebSocket architecture for true real-time transcription of a live audio stream (closer to the original challenge goal).
* **Robust Task Queue:** Migrate the background task from `threading` to a production-grade queue like **Celery & Redis** to handle multiple concurrent users and improve stability.
* **Advanced Lip-Reading:** Integrate a lip-reading (AV-ASR) model as a second modality to improve transcription accuracy in noisy videos.
* **Error Handling:** Improve resilience to edge cases in media files or model outputs.
* **UI/UX:** Enhance the user interface with more feedback and customization options.