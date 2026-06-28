from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.init_db import init_db

from app.routes.auth_routes import router as auth_router
from app.routes.websocket_routes import router as websocket_router
from app.api.routes.upload import router as upload_router
from app.api.routes.audit import router as audit_router
from app.api.routes.email import router as email_router
from app.api.routes.decision import router as decision_router

print("MAIN.PY LOADED")

app = FastAPI(title="Payment Audit Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _on_startup():
    init_db()
    print("INIT_DB COMPLETE")

@app.get("/health")
def health():
    return {"status": "healthy"}

app.include_router(upload_router)
app.include_router(decision_router)
app.include_router(websocket_router)
app.include_router(audit_router)
app.include_router(email_router)
app.include_router(auth_router)