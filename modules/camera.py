import av
import asyncio
from aiortc import VideoStreamTrack

# Kamera-URL
username = "Tapo-Wohnzimmer"
password = "Aa1282198"
ip = "192.168.0.219"
RTSP_URL = f"rtsp://{username}:{password}@{ip}:554/stream1"

class CameraStreamTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.container = None
        self.video_stream = None

    def initialize_stream(self):
        """Wird beim Start des Projekts einmalig aufgerufen, um den RTSP-Stream zu öffnen."""
        try:
            print(f"Verbinde zu: {RTSP_URL}")
            self.container = av.open(RTSP_URL)
            print(f"✅ RTSP-Stream erfolgreich geöffnet")

            video_streams = [s for s in self.container.streams if s.type == 'video']
            if not video_streams:
                print("❌ Kein Videostream in RTSP gefunden.")
                raise RuntimeError("Kein Videostream in RTSP gefunden.")
            self.video_stream = video_streams[0]
            print(f"✅ Videostream gefunden: {self.video_stream}")
        except av.AVError as e:
            print(f"❌ AV-Fehler beim Öffnen des RTSP-Streams: {e}")
        except Exception as e:
            print(f"❌ Fehler beim Initialisieren des Streams: {e}")

    async def recv(self):
        """Hole kontinuierlich Frames aus dem RTSP-Stream"""
        if not self.container:
            print("⚠️ Stream ist noch nicht bereit!")
            await asyncio.sleep(0.01)
            return await self.recv()

        try:
            for packet in self.container.demux(self.video_stream):
                print(f"✅ Packet gefunden: {packet}")
                for frame in packet.decode():
                    print(f"✅ Frame gefunden: {frame}")
                    if isinstance(frame, av.VideoFrame):
                        print(f"✅ VideoFrame gefunden: {frame}")
                        pts, time_base = await self.next_timestamp()
                        frame.pts = pts
                        frame.time_base = time_base
                        return frame
        except Exception as e:
            print(f"❌ Fehler beim Frame-Empfang: {e}")

        await asyncio.sleep(0.01)
        return await self.recv()  # Rekursiv weitermachen

