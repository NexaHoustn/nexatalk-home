import asyncio
import threading
import os
import json
import urllib

from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi import HTTPException, FastAPI, WebSocket, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
from fastapi import WebSocketDisconnect

from datetime import datetime

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay

from modules.system_stats import get_system_data
from modules.open_ai import OpenAiAssistant
from modules.icloud import iCloudService
from modules.recordings import find_all_videos, get_thumbnail_path

pcs = set()
relay = MediaRelay()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai_assistant = OpenAiAssistant()
icloud_client = iCloudService()

STATIC_AUDIO_DIR = "static/audio"
os.makedirs(STATIC_AUDIO_DIR, exist_ok=True)

@app.on_event("startup")
async def on_startup():
    print("Starting up...")

@app.get("/")
async def get():
    html = "<h1>Test</h1>"
    return HTMLResponse(html)

@app.websocket("/system_stats")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            system_data = get_system_data()
            await websocket.send_text(json.dumps(system_data))
            await asyncio.sleep(1)

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

@app.get("/records")
async def get_records():
    records = find_all_videos()
    return JSONResponse(content=records, status_code=200)

@app.get("/thumbnail")
async def get_thumbnail(video_url: str = Query(..., alias="url")):
    video_url_decoded = urllib.parse.unquote(video_url)
    
    thumbnail_path = get_thumbnail_path(video_url_decoded)
    
    if not os.path.isfile(thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail nicht gefunden")

    return FileResponse(
        thumbnail_path,
        media_type="image/jpeg",
        filename=os.path.basename(thumbnail_path)
    )

@app.get("/video")
async def stream_video(request: Request, video_url: str = Query(..., alias="url")):
    # URL dekodieren, um sicherzustellen, dass sie korrekt verarbeitet wird
    video_url_decoded = urllib.parse.unquote(video_url)  
    
    # Nur den relativen Pfad verwenden: Entferne alle absoluten Pfade
    # if video_url_decoded.startswith("/"):
    #     return {"error": "Ungültiger Pfad: Absoluter Pfad ist nicht erlaubt"}

    # Überprüfen, ob die Datei existiert
    if not os.path.isfile(video_url_decoded):
        return {"error": "Datei nicht gefunden"}

    file_size = os.path.getsize(video_url_decoded)
    range_header = request.headers.get("range")

    if range_header:
        # Byte-Range parsen
        range_value = range_header.strip().lower().replace("bytes=", "")
        range_start, range_end = range_value.split("-")
        range_start = int(range_start)
        range_end = int(range_end) if range_end else file_size - 1
        length = range_end - range_start + 1

        def file_stream():
            with open(video_url_decoded, "rb") as f:
                f.seek(range_start)
                yield f.read(length)

        return StreamingResponse(
            file_stream(),
            status_code=206,
            headers={
                "Content-Range": f"bytes {range_start}-{range_end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
                "Content-Type": "video/mp4",
            },
        )
    else:
        return StreamingResponse(
            open(video_url_decoded, "rb"),
            media_type="video/mp4"
        )


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