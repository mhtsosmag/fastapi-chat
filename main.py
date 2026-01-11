
""" from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, List


app = FastAPI()

# Connection Manager
class ConnectionManager:
    def __init__(self):
        self.chat_sockets: Dict[str, Dict[str, WebSocket]] = {}  # room -> username -> ws
        self.user_sockets: Dict[str, List[WebSocket]] = {}       # room -> ws list

    async def connect_chat(self, room: str, username: str, websocket: WebSocket):
        await websocket.accept()
        self.chat_sockets.setdefault(room, {})
        self.chat_sockets[room][username] = websocket

    async def connect_users(self, room: str, websocket: WebSocket):
        await websocket.accept()
        self.user_sockets.setdefault(room, []).append(websocket)
        await websocket.send_json(list(self.chat_sockets.get(room, {}).keys()))

    def disconnect_chat(self, room: str, username: str):
        if room in self.chat_sockets and username in self.chat_sockets[room]:
            del self.chat_sockets[room][username]

    def disconnect_users(self, room: str, websocket: WebSocket):
        if room in self.user_sockets and websocket in self.user_sockets[room]:
            self.user_sockets[room].remove(websocket)

    async def broadcast_chat(self, room: str, message: str):
        for ws in self.chat_sockets.get(room, {}).values():
            await ws.send_text(message)

    async def broadcast_users(self, room: str):
        users = list(self.chat_sockets.get(room, {}).keys())
        for ws in self.user_sockets.get(room, []):
            await ws.send_json(users)

manager = ConnectionManager()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html
@app.get("/")
async def root():
    return FileResponse("static/index.html")

# WebSocket endpoints
@app.websocket("/ws/chat/{room}/{username}")
async def chat_ws(websocket: WebSocket, room: str, username: str):
    await manager.connect_chat(room, username, websocket)
    await manager.broadcast_chat(room, f"🔵 {username} joined the room")
    await manager.broadcast_users(room)

    try:
        while True:
            msg = await websocket.receive_text()
            await manager.broadcast_chat(room, f"{username}: {msg}")

    except WebSocketDisconnect:
        manager.disconnect_chat(room, username)
        await manager.broadcast_chat(room, f"🔴 {username} left the room")
        await manager.broadcast_users(room)

@app.websocket("/ws/users/{room}")
async def users_ws(websocket: WebSocket, room: str):
    await manager.connect_users(room, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_users(room, websocket)
 """


from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid

app = FastAPI()

# Allow CORS for testing on mobile
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve index.html
@app.get("/")
async def root():
    return FileResponse("static/index.html")

# Image upload endpoint
@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    return JSONResponse({"url": f"/static/uploads/{filename}"})


# --- SIMPLE CHAT WEBSOCKET ---
rooms = {}   # room -> set of websockets
users_in_room = {}  # room -> list of usernames

@app.websocket("/ws/chat/{room}/{username}")
async def chat_ws(ws: WebSocket, room: str, username: str):
    await ws.accept()
    rooms.setdefault(room, set()).add(ws)
    users_in_room.setdefault(room, []).append(username)

    # Notify joined
    msg = f"{username} joined"
    for client in rooms[room]:
        await client.send_text(msg)

    try:
        while True:
            data = await ws.receive_text()
            # broadcast to all
            for client in rooms[room]:
                await client.send_text(f"{username}: {data}" if not data.startswith("[image]") else data)
    except:
        pass
    finally:
        rooms[room].remove(ws)
        users_in_room[room].remove(username)
        leave_msg = f"{username} left"
        for client in rooms[room]:
            await client.send_text(leave_msg)


@app.websocket("/ws/users/{room}")
async def users_ws(ws: WebSocket, room: str):
    await ws.accept()
    try:
        while True:
            if room in users_in_room:
                await ws.send_text(str(users_in_room[room]))
    except:
        pass
