import os
from openai import OpenAI
from dotenv import load_dotenv
import tempfile

load_dotenv()

# Sicherstellen, dass der Audio-Ordner existiert
STATIC_AUDIO_DIR = "static/audio"
os.makedirs(STATIC_AUDIO_DIR, exist_ok=True)

class OpenAiAssistant:
    def __init__(self, tts_voice="nova", whisper_model="whisper-1"):
        self.client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))  # OpenAI-Client initialisieren
        self.tts_voice = tts_voice
        self.whisper_model = whisper_model        

    async def get_whisper_response(self, text, websocket):
        """Splittet den Text und sendet ihn Satz für Satz an TTS"""
        splitted_text = text.split("\n\n")
        for text in splitted_text:
            await self.stream_text_to_speech(text, websocket)

    async def stream_text_to_speech(self, text, websocket):
        """ Wandelt Text in Sprache um, speichert und sendet den Stream parallel """
        try:
            # Generiere eine eindeutige Datei im Audio-Ordner
            temp_audio_path = os.path.join(STATIC_AUDIO_DIR, f"tts_{next(tempfile._get_candidate_names())}.wav")

            # Öffne die Datei im Schreibmodus (Binary)
            with open(temp_audio_path, "wb") as audio_file:
                # Text-to-Speech-Stream anfordern (chunked response)
                response = self.client.audio.speech.create(
                    model="tts-1",
                    voice=self.tts_voice,
                    input=text,
                    response_format="wav"  # WAV-Format für höhere Qualität
                )

                # Chunks verarbeiten und gleichzeitig speichern + senden
                for chunk in response.iter_bytes():  
                    audio_file.write(chunk)  # In Datei speichern
                    await websocket.send_bytes(chunk)  # Sofort an WebSocket senden

            print(f"✅ Audio gespeichert unter: {temp_audio_path}")

        except Exception as e:
            print(f"❌ Fehler beim Generieren der Sprachdatei: {e}")
            await websocket.send_text(f"Fehler: {str(e)}")  # Fehler über WebSocket zurückgeben
