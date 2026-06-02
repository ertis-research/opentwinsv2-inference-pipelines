from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1 import automations
from src.database import engine, Base
from src.models import automation # Ensure models are registered

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OpenTrack Engine API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(automations.router, prefix="/api/v1/automations", tags=["automations"])

@app.get("/")
async def root():
    return {"message": "Welcome to OpenTrack Engine API"}
