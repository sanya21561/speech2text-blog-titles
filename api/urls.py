from django.urls import path
from . import views

urlpatterns = [
    # API endpoints will be defined here
    path('transcribe/', views.AudioTranscriptionView.as_view(), name='audio_transcription'),
    path('suggest-titles/', views.BlogTitleSuggestionView.as_view(), name='blog_title_suggestion'),
] 