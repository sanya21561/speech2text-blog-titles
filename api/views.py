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
from .models import TranscriptionResult, TitleSuggestion
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from .serializers import UserSerializer
from django.contrib.auth import authenticate

load_dotenv()
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

if not HUGGINGFACE_TOKEN:
    print("Warning: HUGGINGFACE_TOKEN not found in .env file. Diarization will not work.")

# Global variables to store loaded models
whisper_model = None
diarization_pipeline = None
title_suggestion_pipeline = None
models_loaded = False

def _load_models():
    global whisper_model, diarization_pipeline, title_suggestion_pipeline, models_loaded
    if models_loaded:
        return

    print("Loading models... This may take some time the first time.")
    # Load Whisper model
    whisper_model = whisper.load_model("base", device="cpu")

    # Load Pyannote Audio pipeline (requires HuggingFace token)
    if HUGGINGFACE_TOKEN:
        try:
            diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=HUGGINGFACE_TOKEN
            )
        except Exception as e:
            print(f"Error loading diarization pipeline: {e}")
            diarization_pipeline = None
    else:
        print("HUGGINGFACE_TOKEN not set, diarization pipeline will not be loaded.")

    # Load NLP model for title suggestions
    title_suggestion_pipeline = pipeline("text2text-generation", model="EnglishVoice/t5-base-keywords-to-headline", device="cpu")
    
    models_loaded = True
    print("Models loaded successfully.")

# Create your views here.

class AudioTranscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        _load_models() # Ensure models are loaded when a request comes in

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
                    segment_start = segment['start']
                    segment_end = segment['end']
                    speaker = "Unknown"

                    # Find overlapping diarization turns
                    for turn, _, label in diarization.itertracks(yield_label=True):
                        if max(segment_start, turn.start) < min(segment_end, turn.end):
                            speaker = label
                            break

                    transcription_output.append({
                        "speaker": speaker,
                        "text": segment['text'].strip(),
                        "start_time": segment_start,
                        "end_time": segment_end
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

            # Save transcription result to database
            TranscriptionResult.objects.create(
                audio_file_name=audio_file.name,
                transcription_text=result['text'],
                diarization_json=json.dumps(transcription_output) if diarization_pipeline else None,
                user=request.user 
            )

            return Response({'transcription': transcription_output}, status=status.HTTP_200_OK)

        except Exception as e:
            if os.path.exists('temp_audio.wav'):
                os.remove('temp_audio.wav')
            error_msg = str(e)
            if "temp_audio.wav" in error_msg and "No such file or directory" in error_msg:
                return Response({'error': 'Timed out or file error, please upload your file again for transcription.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BlogTitleSuggestionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        _load_models() # Ensure models are loaded when a request comes in
        content = request.data.get('content')

        if not content:
            return Response({'error': 'No blog post content provided.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Generate title suggestions
            prompt_text = "headline: " + content
            suggestions = []
            for _ in range(3): 
                generated_text = title_suggestion_pipeline(prompt_text, max_new_tokens=20, num_return_sequences=1)[0]['generated_text']
                suggestions.append(generated_text.strip())

            # Save title suggestion result to database
            TitleSuggestion.objects.create(
                original_content=content,
                suggested_titles_json=json.dumps(suggestions),
                user=request.user
            )

            return Response({'suggestions': suggestions}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RegisterUserView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if User.objects.filter(username=username).exists():
            return Response({'error': 'User already registered. Please login.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({'message': 'Registration successful! Please login now!'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginUserView(APIView):
    permission_classes = [AllowAny]
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not User.objects.filter(username=username).exists():
            return Response({'error': 'User not registered.'}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(username=username, password=password)
        if user is None:
            return Response({'error': 'Incorrect password.'}, status=status.HTTP_400_BAD_REQUEST)
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user_id': user.pk, 'username': user.username}, status=status.HTTP_200_OK)

class UserHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        transcriptions = TranscriptionResult.objects.filter(user=user).order_by('-created_at')
        titles = TitleSuggestion.objects.filter(user=user).order_by('-created_at')

        history_data = {
            "transcriptions": [],
            "title_suggestions": []
        }

        for t in transcriptions:
            history_data["transcriptions"].append({
                "id": t.id,
                "audio_file_name": t.audio_file_name,
                "transcription_text": t.transcription_text,
                "diarization_json": json.loads(t.diarization_json) if t.diarization_json else None,
                "created_at": t.created_at.isoformat()
            })
        
        for ts in titles:
            history_data["title_suggestions"].append({
                "id": ts.id,
                "original_content": ts.original_content,
                "suggested_titles": json.loads(ts.suggested_titles_json),
                "created_at": ts.created_at.isoformat()
            })

        return Response(history_data, status=status.HTTP_200_OK)
