from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv
import os
import json

load_dotenv()




app = FastAPI()

rooms = {}

ROOM_PASSWORD = os.getenv("ROOM_PASSWORD")
if not ROOM_PASSWORD:
    raise RuntimeError("ROOM_PASSWORD is not set. Create .env and set ROOM_PASSWORD=...")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    room = (websocket.query_params.get("room") or "").strip()
    key  = (websocket.query_params.get("key")  or "").strip()
    name = (websocket.query_params.get("user") or "").strip()

    if not room or not key or not name:
        await websocket.close(code=1008)
        return

    if key != ROOM_PASSWORD:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    rooms.setdefault(room, {})
    users = rooms[room]

    ws_id = id(websocket)

    if len(users) >= 2:
        await websocket.send_text("[SYS] Chat room full. Try later.")
        await websocket.close(code=1008)
        return

    if name in (u["name"] for u in users.values()):
        await websocket.send_text("[SYS] Name already taken")
        await websocket.close(code=1008)
        return

    users[ws_id] = {"name": name, "websocket": websocket}


    for u in users.values():
        if u["websocket"] is not websocket:
            await u["websocket"].send_text(f"[SYS] {name} joined")

    try:
        while True:
            message = await websocket.receive_text()


            try:
                msg_data = json.loads(message)
                if isinstance(msg_data, dict) and msg_data.get("type") == "file":
                    msg_data["sender"] = name
                    broadcast_msg = json.dumps(msg_data)

                    for u in users.values():
                        if u["websocket"] is not websocket:
                            await u["websocket"].send_text(broadcast_msg)
                    continue
            except json.JSONDecodeError:
                pass


            for u in users.values():
                if u["websocket"] is not websocket:
                    await u["websocket"].send_text(f"[{name}] {message}")

    finally:
        users.pop(ws_id, None)

        for u in users.values():
            await u["websocket"].send_text(f"[SYS] {name} left")

        if not users:
            rooms.pop(room, None)