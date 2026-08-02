import asyncio
import logging
import os
from dotenv import load_dotenv
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import httpx
from mail import send_contact_email
from fastapi.concurrency import run_in_threadpool
from fastapi import FastAPI, APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Change this to your own GitHub username
GITHUB_USER = os.environ.get("GITHUB_USERNAME", "Vijay8161")
GITHUB_API = "https://api.github.com"
GH_CACHE_TTL = 1800
_gh_cache = {"ts": 0.0, "data": None}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ContactMessageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=1, max_length=5000)


class ContactMessage(ContactMessageCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@api_router.get("/health")
async def health():
    return {"status": "ok"}


@api_router.post("/contact", status_code=201)
async def create_contact(payload: ContactMessageCreate):
    try:
        await run_in_threadpool(
            send_contact_email,
            payload.name,
            payload.email,
            payload.message,
        )

        logger.info("Contact email sent from %s", payload.email)

        return {
            "ok": True,
            "message": "Your message has been sent successfully.",
        }

    except Exception as exc:
        logger.exception("Failed to send contact email")

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

@api_router.get("/github/overview")
async def github_overview():
    now = time.time()
    if _gh_cache["data"] and now - _gh_cache["ts"] < GH_CACHE_TTL:
        return _gh_cache["data"]

    headers={
               "User-Agent": "portfolio-app", 
               "Accept": "application/vnd.github+json",
               "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            }
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as http:
            user_r, repos_r = await asyncio.gather(
                http.get(f"{GITHUB_API}/users/{GITHUB_USER}"),
                http.get(f"{GITHUB_API}/users/{GITHUB_USER}/repos", params={"per_page": 100, "sort": "pushed"}),
            )
            user_r.raise_for_status()
            repos_r.raise_for_status()

            own = [r for r in repos_r.json() if not r.get("fork")]
            lang_responses = await asyncio.gather(
                *[http.get(r["languages_url"]) for r in own[:12]], return_exceptions=True
            )
            languages = {}
            for lr in lang_responses:
                if isinstance(lr, Exception) or getattr(lr, "status_code", 500) != 200:
                    continue
                for lang, size in lr.json().items():
                    languages[lang] = languages.get(lang, 0) + size

            u = user_r.json()
            data = {
                "user": {
                    "login": u["login"],
                    "avatar_url": u["avatar_url"],
                    "html_url": u["html_url"],
                    "public_repos": u["public_repos"],
                    "followers": u["followers"],
                    "following": u["following"],
                    "created_at": u["created_at"],
                },
                "languages": languages,
                "repos": [
                    {
                        "name": r["name"],
                        "description": r["description"],
                        "language": r["language"],
                        "stars": r["stargazers_count"],
                        "forks": r["forks_count"],
                        "pushed_at": r["pushed_at"],
                        "html_url": r["html_url"],
                        "homepage": r.get("homepage"),
                    }
                    for r in own
                ],
                "fetched_at": now,
            }
            _gh_cache.update(ts=now, data=data)
            return data
    except Exception as exc:
        logger.warning("GitHub fetch failed: %s", exc)
        if _gh_cache["data"]:
            return _gh_cache["data"]
        raise HTTPException(status_code=502, detail="github_unavailable")



app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)