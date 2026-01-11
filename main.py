
""" from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get():
    return FileResponse("static/index.html")


# ---------------- WebSocket Chat ----------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}  # room -> list of websockets
        self.usernames: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, room: str, username: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)
        self.usernames[websocket] = username
        await self.broadcast_system(room, f"{username} joined the room")
        await self.send_user_list(room)

    def disconnect(self, websocket: WebSocket, room: str):
        username = self.usernames.get(websocket, "Unknown")
        if room in self.active_connections:
            if websocket in self.active_connections[room]:
                self.active_connections[room].remove(websocket)
        self.usernames.pop(websocket, None)
        return username

    async def send_personal(self, websocket: WebSocket, message: str):
        await websocket.send_text(message)

    async def broadcast(self, room: str, message: str):
        for connection in self.active_connections.get(room, []):
            await connection.send_text(message)

    async def broadcast_system(self, room: str, message: str):
        await self.broadcast(room, f"[SYSTEM] {message}")

    async def send_user_list(self, room: str):
        users = [self.usernames[c] for c in self.active_connections.get(room, [])]
        for connection in self.active_connections.get(room, []):
            await connection.send_json(users)


manager = ConnectionManager()


@app.websocket("/ws/chat/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str):
    await manager.connect(websocket, room, username)
    try:
        while True:
            data = await websocket.receive_text()
            # Check if it's a photo
            if data.startswith("[PHOTO]"):
                # Broadcast the photo to all users
                await manager.broadcast(room, data)
            else:
                await manager.broadcast(room, f"{username}: {data}")
    except WebSocketDisconnect:
        user_left = manager.disconnect(websocket, room)
        await manager.broadcast_system(room, f"{user_left} left the room")
        await manager.send_user_list(room)


@app.websocket("/ws/users/{room}")
async def users_endpoint(websocket: WebSocket, room: str):
    await websocket.accept()
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
 """

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict
import os
import base64
import uuid

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Folder to store uploaded photos
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
async def get_index():
    return FileResponse("static/index.html")


# ---------------- WebSocket Chat ----------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}  # room -> list of websockets
        self.usernames: Dict[WebSocket, str] = {}
        self.photos: Dict[str, List[str]] = {}  # room -> list of photo URLs

    async def connect(self, websocket: WebSocket, room: str, username: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
            self.photos[room] = []  # init photo history
        self.active_connections[room].append(websocket)
        self.usernames[websocket] = username
        await self.broadcast_system(room, f"{username} joined the room")
        # Send existing photos to the newly joined user
        for photo_url in self.photos[room]:
            await websocket.send_text(f"[PHOTO]{photo_url}")

    def disconnect(self, websocket: WebSocket, room: str):
        username = self.usernames.get(websocket, "Unknown")
        if room in self.active_connections:
            if websocket in self.active_connections[room]:
                self.active_connections[room].remove(websocket)
        self.usernames.pop(websocket, None)
        return username

    async def broadcast(self, room: str, message: str):
        for connection in self.active_connections.get(room, []):
            await connection.send_text(message)

    async def broadcast_system(self, room: str, message: str):
        await self.broadcast(room, f"[SYSTEM]{message}")


manager = ConnectionManager()


@app.websocket("/ws/chat/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str):
    await manager.connect(websocket, room, username)
    try:
        while True:
            data = await websocket.receive_text()
            if data.startswith("[PHOTO]"):
                b64_data = data.replace("[PHOTO]", "")
                try:
                    header, encoded = b64_data.split(",", 1)
                    ext = header.split("/")[1].split(";")[0]  # jpg, png
                    filename = f"{uuid.uuid4()}.{ext}"
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    with open(file_path, "wb") as f:
                        f.write(base64.b64decode(encoded))
                    photo_url = f"/static/uploads/{filename}"
                    manager.photos[room].append(photo_url)
                    await manager.broadcast(room, f"[PHOTO]{photo_url}")
                except Exception as e:
                    print("Failed to save photo:", e)
            else:
                await manager.broadcast(room, f"{username}: {data}")
    except WebSocketDisconnect:
        user_left = manager.disconnect(websocket, room)
        await manager.broadcast_system(room, f"{user_left} left the room")

