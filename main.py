
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


from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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

