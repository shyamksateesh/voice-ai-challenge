# Screenshots for README

This folder contains screenshots for the main README documentation.

## Required Screenshots

Please add the following screenshots to this folder:

### 1. homepage.png
**What to capture**: Full view of the main LyrAssist homepage
- Show the complete upload form
- Include all configuration options (model selection, checkboxes)
- Make sure the "How to Use This Tool" button is visible in the top right
- Capture in a clean state (no files selected)

**How to take**:
- Open `http://127.0.0.1:5001` in your browser
- Take a full-page screenshot or crop to show the main content area

---

### 2. upload-interface.png
**What to capture**: Close-up of the upload section
- Focus on the file upload button
- Show the supported formats text (Video: MP4, MOV, AVI | Audio: MP3, WAV, M4A)
- Include the OR separator and recording buttons
- Optionally show a file selected with the green feedback text

**How to take**:
- Select a file to show the validation feedback
- Zoom in or crop to focus on just the upload section

---

### 3. processing-view.png
**What to capture**: Screenshot during active processing
- Show the status message ("Processing... See log below")
- Capture the live log box with actual processing logs
- Make sure multiple log entries are visible
- Show the spinner/loading state

**How to take**:
- Upload a file and click "Start Processing"
- Wait a few seconds for logs to appear
- Take screenshot while processing is active

---

### 4. result-view.png
**What to capture**: Complete results page after processing
- Show the video player with a processed video loaded
- Include all three buttons (Download Video, Download Transcript, Process Another File)
- Show at least part of the interactive lyrics section below
- Capture the "Processing Complete!" status message

**How to take**:
- Wait for processing to complete
- Scroll to show the video player and buttons
- Take a full screenshot of the result area

---

### 5. interactive-lyrics.png
**What to capture**: Close-up of the interactive lyrics feature
- Focus on the lyrics text section
- Show multiple lines of lyrics with the Spotify-style formatting
- Hover over a line to capture the hover effect (gray background)
- Make sure the clickable words are clearly visible

**How to take**:
- Scroll down to the lyrics section after processing completes
- Hover over one of the lyric lines to show the hover effect
- Crop tightly to focus on just the lyrics area

---

## Tips for Best Screenshots

1. **Use a clean browser window** - Hide bookmarks bar, close unnecessary tabs
2. **Use consistent window size** - Around 1400px width works well
3. **Ensure good contrast** - The dark theme should show clearly
4. **Capture actual content** - Use real transcription results, not placeholders
5. **Save as PNG** - Better quality than JPG for UI screenshots
6. **Optimize file size** - Keep images under 1MB each if possible

## Screenshot Tools

- **macOS**: Cmd+Shift+4 (select area) or Cmd+Shift+3 (full screen)
- **Windows**: Snipping Tool or Win+Shift+S
- **Chrome DevTools**: Cmd/Ctrl+Shift+P → "Capture screenshot"
