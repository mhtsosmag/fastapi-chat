from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        self.chat_sockets: Dict[str, Dict[str, WebSocket]] = {}   # room -> username -> ws
        self.user_sockets: Dict[str, List[WebSocket]] = {}        # room -> ws list

    async def connect_chat(self, room: str, username: str, websocket: WebSocket):
        await websocket.accept()
        self.chat_sockets.setdefault(room, {})
        self.chat_sockets[room][username] = websocket

    async def connect_users(self, room: str, websocket: WebSocket):
        await websocket.accept()
        self.user_sockets.setdefault(room, []).append(websocket)
        # Send current user list immediately
        await self.broadcast_users(room)

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
