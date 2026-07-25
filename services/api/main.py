import os
import json
import string
import random
import logging
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, HttpUrl
import redis

from database import engine, get_db, Base
import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener API", version="1.0.0")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

CLICK_QUEUE = "clicks:queue"
CACHE_TTL = 3600

class URLCreate(BaseModel):
    url: HttpUrl

class URLResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str

def generate_short_code(length: int = 6) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        redis_client.ping()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.post("/shorten", response_model=URLResponse)
def shorten(payload: URLCreate, db: Session = Depends(get_db)):
    for _ in range(5):
        code = generate_short_code()
        existing = db.query(models.URL).filter(models.URL.short_code == code).first() #first serve 
        if not existing: #se existing for None significa que nao existe nenhum registro com esse codigo, entao pode usar
            break
    else: # se sair sem o brake, entra no else
        raise HTTPException(status_code=500, detail="Could not generate unique code")

    url_entry = models.URL(short_code=code, original_url=str(payload.url))
    db.add(url_entry)
    db.commit()
    db.refresh(url_entry)

    redis_client.setex(f"url:{code}", CACHE_TTL, str(payload.url))

    return URLResponse(
        short_code=code,
        short_url=f"{BASE_URL}/{code}",
        original_url=str(payload.url),
    )

@app.get("/{short_code}")
def redirect(short_code: str, request: Request, 
             db: Session = Depends(get_db)):
        #Exemplo de chamada:
        #redirect( "abc123", 
    
    cached = redis_client.get(f"url:{short_code}")
    #cached recebe o valor do redis da url encurtada, se nao tiver no redis, vai ser None
    if cached:
        original = cached
    else:
        #caso nao tenha no redis, vai buscar no banco de dados
        url_entry = db.query(models.URL).filter(models.URL.short_code == short_code).first()
        if not url_entry:
            raise HTTPException(status_code=404, detail="Short code not found")
        #agora que encontrou no banco, vai colocar no redis para cachear
        original = url_entry.original_url
        redis_client.setex(f"url:{short_code}", CACHE_TTL, original)

    #se chegou aqui,
    # significa que encontrou a url original, seja no cache ou no banco de dados
    #agora vai registrar o evento de clique no redis
    event = {
        "short_code": short_code,
        "user_agent": request.headers.get("user-agent", ""),
        "ip_address": request.client.host if request.client else "",
    } #este é o formato de evento de clique
    redis_client.rpush(CLICK_QUEUE, json.dumps(event))
    #json.dumps serve para converter o dicionário em uma string JSON

    return RedirectResponse(url=original, status_code=302)

@app.get("/stats/{short_code}")
def stats(short_code: str, db: Session = Depends(get_db)):
    url_entry = db.query(models.URL).filter(models.URL.short_code == short_code).first()
    if not url_entry:
        raise HTTPException(status_code=404, detail="Short URL not found")
    count = db.query(models.ClickEvent).filter(models.ClickEvent.short_code == short_code).count()
    return {
        "short_code": short_code,
        "original_url": url_entry.original_url,
        "total_clicks": count,
    }
    