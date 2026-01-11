
""" from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse  # <-- import here
from manager import ConnectionManager 

app = FastAPI()
manager = ConnectionManager()

# Serve static files from "static" folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add a route for "/" to serve index.html
@app.get("/")
async def root():
    return FileResponse("static/index.html")  # <-- put here

# WebSocket route for chat
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

# WebSocket route for user list
@app.websocket("/ws/users/{room}")
async def users_ws(websocket: WebSocket, room: str):
    await manager.connect_users(room, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_users(room, websocket)
        await manager.broadcast_users(room) """





from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
    return FileResponse("static/chat.html")

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

