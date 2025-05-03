# AI Video Highlight Generator

This project is a Flask-based web application that allows users to upload video files, automatically extract audio, generate transcripts, detect topics via an AI API, and create a highlight video based on relevant segments or keywords.

## Features

- **Video Upload**: Drag &#38; drop or browse to select and upload video files (max 100MB).
- **Audio Extraction**: Extracts audio from the video and converts it to WAV format.
- **Parallel Transcription**: Splits the audio into 5-second chunks and transcribes them in parallel using Google Speech Recognition.
- **Topic Detection**: Sends the transcript to an AI API (e.g., Llama 3.3) to determine the topic and relevant sentences.
- **Keyword Search**: Allows optional keyword input; if omitted, uses the AI-detected topic.
- **Clip Extraction**: Finds time intervals in the transcript matching the keyword or AI-provided timestamps.
- **Merging Overlaps**: Merges clips that are within a 5-second threshold.
- **Highlight Video Creation**: Cuts and concatenates selected clips into a final highlights video.
- **Download Result**: Serves the generated highlight video for download.

## Prerequisites

- Python 3.8+
- [FFmpeg](https://ffmpeg.org/) installed and available in your PATH
- Linux, macOS, or Windows

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/dravex01/video-highlight-generator.git
   cd video-highlight-generator
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate    # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ensure FFmpeg is installed**
   ```bash
   ffmpeg -version
   ```

## Configuration

1. **API Key**: Replace the placeholder API key in `app.py` with your own:
   ```python
   api_key = "YOUR_API_KEY_HERE"
   ```

2. **API Endpoint**: If using a different AI service, update the `url` and request payload in `app.py`.

3. **Folders**: By default, the app creates two directories in the project root:
   - `uploads/`: Stores uploaded video and temporary audio.
   - `output/`: Stores generated clips and the final highlight video.

4. **Settings**: Adjust transcription chunk length, merge threshold, or video presets in `app.py` as needed.

## Usage

1. **Run the Flask app**
   ```bash
   export FLASK_APP=app.py
   flask run --host=0.0.0.0 --port=5000
   ```
   Or with debug mode:
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to `http://localhost:5000`

3. **Upload a video** and optionally enter a keyword to highlight parts of the video relevant to that term.

4. **Click** "Process Video" and wait for the processing to complete.

5. **Download** the resulting highlight video when the link appears.


## API Endpoints

- **GET /**
  - Renders the upload form (`index.html`).

- **POST /process**
  - Expects `video` file and optional `keyword`.
  - Returns the final highlight video as an attachment on success, or an error message.

## Dependencies

Key Python libraries used:

- Flask
- Requests
- MoviePy
- SpeechRecognition
- Pydub

Install all dependencies via:
```bash
pip install flask requests moviepy SpeechRecognition pydub
```

## Troubleshooting

- **FFmpeg errors**: Ensure FFmpeg is installed and accessible from your shell.
- **API errors**: Verify your API key and endpoint URL.
- **Large videos**: Adjust the maximum upload size and chunk length if needed.

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

