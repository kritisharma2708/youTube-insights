from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from app.config import APP_API_KEY
from app.database import Base, engine
from app.routers import feed, videos

Base.metadata.create_all(bind=engine)

app = FastAPI(title="InsightClips", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    if not APP_API_KEY:
        return  # No key configured = dev mode
    if api_key != APP_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")


app.include_router(
    feed.router, prefix="/api", tags=["feed"], dependencies=[Depends(verify_api_key)]
)
app.include_router(
    videos.router, prefix="/api", tags=["videos"], dependencies=[Depends(verify_api_key)]
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
