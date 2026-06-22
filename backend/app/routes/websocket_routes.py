from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import WebSocketDisconnect

from app.services.websocket_manager import manager

router = APIRouter()

@router.websocket("/ws/{role}")
async def websocket_endpoint(
    websocket: WebSocket,
    role: str
):
    print(f"WEBSOCKET CONNECTED: {role}")

    await manager.connect(
        websocket,
        role
    )

    try:
        while True:
            data = await websocket.receive_text()
            print("Received:", data)

    except WebSocketDisconnect:
        print(f"WEBSOCKET DISCONNECTED: {role}")

        manager.disconnect(
            websocket,
            role
        )