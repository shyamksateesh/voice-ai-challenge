# Lyric Agent: A Web-Based AI Transcription & Video Tool

A functional prototype of an AI agent that transcribes audio/video files and renders synchronized subtitles. This project provides a web interface for processing media with configurable AI models on a local server.

## Overview

This project is an AI-powered media processing pipeline wrapped in a Flask web application. It solves the problem of manually transcribing audio and creating subtitles by automating the entire workflow.

A user can upload a video/audio file or record new audio directly in the browser. The backend server (running locally) processes the media using state-of-the-art AI models and then composites a new video file with synchronized, phrase-level subtitles.

This serves as a powerful prototype for accessibility tools (real-time captioning) and creative workflows (lyric video generation).

## Core Features

* **Simple Web UI:** A clean interface to upload media, record new audio, and select processing options.
* **Asynchronous Backend:** Uses Flask and background threading to handle long-running tasks (like transcription and video rendering) without timing out the browser.
* **Modular Pipeline:** The backend is refactored into a scalable, multi-file structure (`pipeline.py`, `audio_processing.py`, `transcription.py`, `video_processing.py`).
* **Configurable AI Options:**
    * **Vocal Separation:** Checkbox to enable `demucs` to isolate vocals from music before transcription.
    * **Whisper Model:** Selectable model size (`small`, `medium`, `large`) to balance speed and accuracy.
    * **Karaoke Mode:** An *experimental* option to generate a "word-wipe" karaoke-style video.
* **Dynamic Video Rendering:**
    * **Responsive Subtitles:** Text is dynamically resized to fit any video dimension, from portrait to landscape.
    * **Audio-Only Mode:** Automatically generates a 720p black-screen video for `.mp3` or `.wav` inputs.
    * **Embedded Player:** The final processed video is embedded directly on the page for playback, with a separate download link.

## Tech Stack

* **Backend:** Python, Flask
* **Frontend:** HTML5, Tailwind CSS, JavaScript (MediaRecorder API)
* **AI/ML:** OpenAI Whisper (Transcription), Demucs (Vocal Separation)
* **Media Processing:** MoviePy (Video Compositing), Pydub (Audio Handling)

## How to Run This Project

### 1. Prerequisites

* Python 3.10+
* FFmpeg (required by `moviepy` and `pydub`)
* (On macOS) `h264_videotoolbox` is used for hardware-accelerated video encoding.

### 2. Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/voice-ai-challenge.git](https://github.com/your-username/voice-ai-challenge.git)
    cd voice-ai-challenge
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    *(This may take time as it includes PyTorch and Demucs)*
    ```bash
    pip install flask pydub openai-whisper moviepy numpy demucs torch torchaudio torchcodec
    ```

4.  **Create required folders:**
    The application needs these folders to function.
    ```bash
    mkdir uploads
    mkdir outputs
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
    * Choose your processing options.
    * Click "Start Processing" and wait for the UI to update.

## Future Work (Roadmap)

This prototype is the foundation for a more robust, real-time application.

* **Real-Time Streaming:** Implement a WebSocket architecture for true real-time transcription of a live audio stream.
* **Robust Task Queue:** Migrate the background task from `threading` to a production-grade queue like **Celery & Redis** to handle multiple concurrent users and improve stability.
* **Advanced Lip-Reading:** Integrate a lip-reading (AV-ASR) model as a second modality to improve transcription accuracy in noisy videos.
* **User Database:** Add a database to store user files and processing history.
