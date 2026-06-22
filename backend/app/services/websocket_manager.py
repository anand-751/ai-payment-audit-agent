from fastapi import WebSocket

class ConnectionManager:

    def __init__(self):
        self.active_connections = {
            "ap": [],
            "cfo": []
        }

    async def connect(
        self,
        websocket: WebSocket,
        role: str
    ):
        await websocket.accept()

        if role not in self.active_connections:
            self.active_connections[role] = []

        self.active_connections[role].append(
            websocket
        )

    def disconnect(
        self,
        websocket: WebSocket,
        role: str
    ):
        if (
            role in self.active_connections
            and websocket in self.active_connections[role]
        ):
            self.active_connections[role].remove(
                websocket
            )

    async def notify_role(
        self,
        role: str,
        payload: dict
    ):
        connections = self.active_connections.get(
            role,
            []
        )

        dead_connections = []

        for connection in connections:
            try:
                await connection.send_json(
                    payload
                )
            except:
                dead_connections.append(
                    connection
                )

        for dead in dead_connections:
            self.active_connections[role].remove(
                dead
            )

manager = ConnectionManager()