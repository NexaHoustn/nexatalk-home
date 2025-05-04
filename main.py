import asyncio
import threading
import os
import json
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel
from modules.open_ai import OpenAiAssistant
from modules.icloud import iCloudService
from fastapi import HTTPException
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
from fastapi import WebSocketDisconnect

from datetime import datetime

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay
from modules.system_stats import get_system_data
pcs = set()
relay = MediaRelay()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Erlaubt Anfragen von diesem Origin
    allow_credentials=True,
    allow_methods=["*"],  # Erlaubt alle HTTP-Methoden (GET, POST, etc.)
    allow_headers=["*"],  # Erlaubt alle Header
)

openai_assistant = OpenAiAssistant()
icloud_client = iCloudService()

STATIC_AUDIO_DIR = "static/audio"
os.makedirs(STATIC_AUDIO_DIR, exist_ok=True)

@app.on_event("startup")
async def on_startup():
    """Starte den Stream beim Start der Anwendung."""
    # loop = asyncio.get_event_loop()

@app.get("/")
async def get():
    html = "<h1>Test</h1>"
    return HTMLResponse(html)

@app.websocket("/system_stats")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # Alle 5 Sekunden Systemdaten abrufen
            system_data = get_system_data()
            # Systemdaten als JSON über WebSocket senden
            await websocket.send_text(json.dumps(system_data))
            
            # # Warte 5 Sekunden, bevor die Daten erneut gesendet werden
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        print("Client disconnected")

    except Exception as e:
        print(f"Fehler beim Verarbeiten der WebSocket-Verbindung: {e}")
        await websocket.send_text(f"Fehler: {str(e)}")

@app.websocket("/openai/whisper/tts")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # Empfang von Text-Nachricht über den WebSocket
            text = await websocket.receive_text()

            await openai_assistant.get_whisper_response(text, websocket)

    except Exception as e:
        print(f"Fehler beim Verarbeiten der Anfrage: {e}")
        await websocket.send_text(f"Fehler: {str(e)}")

@app.websocket("/cams")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # Empfang von Text-Nachricht über den WebSocket
            text = await websocket.receive_text()

            print(text)

    except Exception as e:
        print(f"Fehler beim Verarbeiten der Anfrage: {e}")
        await websocket.send_text(f"Fehler: {str(e)}")

class iCloudAuth(BaseModel):
    email: str
    password: str

class EventRange(BaseModel):
    start: str
    end: str

def get_default_timeframe(): #current month
    """Setzt den Standardzeitraum auf den aktuellen Monat"""
    today = datetime.today()
    start = today.replace(day=1).strftime("%Y-%m-%d")  # Erster Tag des Monats
    next_month = today.replace(day=28) + timedelta(days=4)  # Sicher in nächsten Monat springen
    end = next_month.replace(day=1) - timedelta(days=1)  # Letzter Tag des Monats
    end = end.strftime("%Y-%m-%d")
    return {"start": start, "end": end}

@app.post("/icloud/events")
async def get_events_by_timeframe(creds: iCloudAuth, range: Optional[EventRange] = None):
    """Dynamische Authentifizierung bei jedem Request"""
    if range is None:
        range_values = get_default_timeframe()
        range = EventRange(**range_values)

    try:
        # Neue Instanz von iCloudService mit den übergebenen Anmeldedaten
        icloud_service = iCloudService(email=creds.email, password=creds.password)
        icloud_service.authenticate()  # Authentifizierung durchführen
        
        events = icloud_service.get_calendar_events_in_range(range)
        return events

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/icloud/devices")
async def get_iphone_data(creds: iCloudAuth):
    """Dynamische Authentifizierung bei jedem Request"""
    try:
        # Neue Instanz von iCloudService mit den übergebenen Anmeldedaten
        icloud_service = iCloudService(email=creds.email, password=creds.password)
        icloud_service.authenticate()  # Authentifizierung durchführen

        print(creds)
        
        data = icloud_service.get_devices()
        # return data
        return JSONResponse(content=data, status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class RingDevice(BaseModel):
    device_id: str

@app.post("/icloud/devices/ring")
async def ring_device(creds: iCloudAuth, ring_device: RingDevice):
    """Dynamische Authentifizierung bei jedem Request"""
    try:
        icloud_service = iCloudService(email=creds.email, password=creds.password)
        icloud_service.authenticate()

        print(creds)
        print(ring_device)

        data = icloud_service.ring_device(ring_device.device_id)  

        return JSONResponse(content={"status": "success", "data": data}, status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# class CalendarRequest(BaseModel):
#     start: str  # Startzeit als String
#     end: str    # Endzeit als String

#     def to_datetime(self):
#         """Konvertiere Start- und Endzeit in datetime-Objekte."""
#         return (
#             datetime.fromisoformat(self.start.replace("Z", "+00:00")),
#             datetime.fromisoformat(self.end.replace("Z", "+00:00"))
#         )

# @app.post("/icloud/events")
# async def get_events_in_range(request: CalendarRequest):
#     try:
#         print(request)
        
#         start_dt, end_dt = request.to_datetime()
        
#         # Holen der Events für den angegebenen Zeitraum
#         events = calendar_client.get_events_in_range(start_dt, end_dt)
        
#         # Rückgabe der Events als JSON
#         return events
    
#     except ValueError as e:
#         # Falls der Datumsstring ungültig ist
#         return JSONResponse(content={"error": f"Invalid date format: {e}"}, status_code=400)
    
#     except Exception as e:
#         # Allgemeine Fehlerbehandlung
#         return JSONResponse(content={"error": str(e)}, status_code=500)