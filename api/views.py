from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from dotenv import load_dotenv
import os
import whisper
from pyannote.audio import Pipeline
import json
import torchaudio
import numpy as np
from transformers import pipeline

load_dotenv()
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

if not HUGGINGFACE_TOKEN:
    print("Warning: HUGGINGFACE_TOKEN not found in .env file. Diarization will not work.")

# Load Whisper model
whisper_model = whisper.load_model("base")

# Load Pyannote Audio pipeline (requires HuggingFace token)
diarization_pipeline = None
if HUGGINGFACE_TOKEN:
    try:
        diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=HUGGINGFACE_TOKEN
        )
    except Exception as e:
        print(f"Error loading diarization pipeline: {e}")
        diarization_pipeline = None

# Load NLP model for title suggestions
title_suggestion_pipeline = pipeline("text2text-generation", model="Babelscape/t5-large-generation-tldr")

# Create your views here.

class AudioTranscriptionView(APIView):
    def post(self, request, *args, **kwargs):
        if 'audio_file' not in request.FILES:
            return Response({'error': 'No audio file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        audio_file = request.FILES['audio_file']

        try:
            # Save the uploaded audio file temporarily
            with open('temp_audio.wav', 'wb+') as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)

            # Load audio for Whisper
            whisper_audio = whisper.load_audio('temp_audio.wav')
            
            # Transcribe with Whisper
            result = whisper_model.transcribe(whisper_audio, word_timestamps=True, language='en')
            segments = result['segments']

            transcription_output = []

            if diarization_pipeline:
                # Diarization with pyannote.audio
                waveform, sample_rate = torchaudio.load('temp_audio.wav')
                diarization = diarization_pipeline({"waveform": waveform, "sample_rate": sample_rate})

                # Process segments and assign speakers
                for segment in segments:
                    start = segment['start']
                    end = segment['end']
                    text = segment['text']
                    
                    speaker = "UNKNOWN_SPEAKER"
                    # Find dominant speaker in the segment
                    for turn, track, label in diarization.crop(f={"waveform": waveform, "sample_rate": sample_rate}, focus=segment):
                        speaker = label
                        break # Take the first speaker found in the segment

                    transcription_output.append({
                        "speaker": speaker,
                        "text": text.strip(),
                        "start_time": start,
                        "end_time": end
                    })
            else:
                # No diarization, just transcription
                for segment in segments:
                    transcription_output.append({
                        "speaker": "", # No speaker info without diarization
                        "text": segment['text'].strip(),
                        "start_time": segment['start'],
                        "end_time": segment['end']
                    })

            os.remove('temp_audio.wav') # Clean up temp file

            return Response({'transcription': transcription_output}, status=status.HTTP_200_OK)

        except Exception as e:
            if os.path.exists('temp_audio.wav'):
                os.remove('temp_audio.wav')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BlogTitleSuggestionView(APIView):
    def post(self, request, *args, **kwargs):
        content = request.data.get('content')

        if not content:
            return Response({'error': 'No blog post content provided.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Generate title suggestions
            # We'll generate a single long summary and then split it into 3 parts,
            # or generate 3 distinct short summaries if the model supports it.
            # For simplicity, let's assume the model generates one summary.
            # We'll then try to split it or make multiple calls if needed.

            # A common approach for title generation is to use a summarization model
            # and then potentially rephrase/extract keywords for multiple titles.
            # Since the model is 't5-large-generation-tldr', it's designed for 'Too Long; Didn't Read'
            # which means summarization. We'll generate a few short summaries.
            
            suggestions = []
            for _ in range(3): # Attempt to generate 3 distinct suggestions
                # For a tldr model, we might need to prompt it differently or extract different aspects
                # For now, let's just use the default generation and take the first few words as a title
                # In a more advanced scenario, we'd fine-tune a model for title generation specifically
                generated_text = title_suggestion_pipeline(content, max_new_tokens=20, num_return_sequences=1, do_sample=True, top_k=50, top_p=0.95)[0]['generated_text']
                suggestions.append(generated_text.strip())

            return Response({'suggestions': suggestions}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
