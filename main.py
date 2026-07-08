from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routes.upload import upload_router
from routes.analyze import  analyze_router
from routes.chat import  chat_router

# Load environment variables
load_dotenv()

app = FastAPI(
    title="AI Business Intelligence Backend",
    version="2.0.0",
)

# CORS (Hackathon Demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(upload_router, tags=["Upload"])
app.include_router(analyze_router, tags=["Analysis"])
app.include_router(chat_router, tags=["AI Chat"])


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "AI Business Intelligence Backend Running 🚀"
    }