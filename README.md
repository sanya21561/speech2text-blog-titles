# Speech2Text Blog Titles

A Django application that provides audio transcription with speaker diarization and AI-powered blog title suggestions.

## Features

1. **Audio Transcription with Diarization**
   - Transcribes audio files using OpenAI's Whisper
   - Identifies different speakers using pyannote.audio
   - Supports multiple languages
   - Returns structured JSON output

2. **AI Blog Title Suggestions**
   - Generates 3 potential titles for blog posts
   - Uses `pszemraj/long-t5-tglobal-xl-16384-book-summary` model from HuggingFace for NLP
   - RESTful API endpoint for easy integration

## Setup Instructions

1. Create a virtual environment:
```bash
python3.11 -m venv venv311
source venv311/bin/activate  # On Windows: venv311\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the project root with:
```
HUGGINGFACE_TOKEN=your_huggingface_token
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Start the development server:
```bash
python manage.py runserver
```

## API Endpoints

### 1. Audio Transcription with Diarization
- **Endpoint**: `/api/transcribe/`
- **Method**: POST
- **Input**: Audio file (supported formats: wav, mp3)
- **Output**: JSON with transcription and speaker information

Example response:
```json
{
    "transcription": [
        {
            "speaker": "SPEAKER_1",
            "text": "Hello, how are you?",
            "start_time": 0.0,
            "end_time": 2.5
        },
        {
            "speaker": "SPEAKER_2",
            "text": "I'm doing great, thank you!",
            "start_time": 2.5,
            "end_time": 4.8
        }
    ]
}
```

### 2. Blog Title Suggestions
- **Endpoint**: `/api/suggest-titles/`
- **Method**: POST
- **Input**: Blog post content
- **Output**: JSON with 3 title suggestions

Example response:
```json
{
    "suggestions": [
        "The Future of AI in Healthcare",
        "How AI is Revolutionizing Medical Diagnosis",
        "AI and Healthcare: A Perfect Partnership"
    ]
}
```

## Note
This project requires a HuggingFace token for accessing models like `pyannote.audio`. You can obtain a token by:
1. Creating an account on HuggingFace.
2. Visiting the model page (e.g., `https://hf.co/pyannote/speaker-diarization-3.1`) and accepting the user conditions, if prompted.
3. Generating a token in your HuggingFace account settings (Profile -> Settings -> Access Tokens).

## Demo

You can try out the diarization and transcription feature using the provided example audio file and see the expected output.

**Example files:**
- `speech2text_example/Conversation 1.mp3` — Example audio file with multiple speakers.
- `speech2text_example/conversation1_transcription.png` — Screenshot of the diarized transcription result.

**How it works:**
1. Go to the web interface.
2. Upload `Conversation 1.mp3` from the `speech2text_example` folder.
3. Click **Transcribe**.
4. You will see a diarized, speaker-separated transcript similar to the screenshot below.

![Diarized Transcription Example](speech2text_example/conversation1_transcription.png)

--- 