from django.db import models
from django.conf import settings # Import settings to reference AUTH_USER_MODEL

# Create your models here.

class TranscriptionResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    audio_file_name = models.CharField(max_length=255, blank=True, null=True)
    transcription_text = models.TextField()
    diarization_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transcription for {self.audio_file_name or 'untitled'} by {self.user or 'Anonymous'} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class TitleSuggestion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    original_content = models.TextField()
    suggested_titles_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Title suggestion for {self.user or 'Anonymous'} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
