#!/usr/bin/env python3
"""
Railway 프로덕션용 yt-dlp FastAPI 서버
완전히 새로운 배포 - 캐시 문제 해결
"""

import os
import time
import logging
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import uvicorn

# yt-dlp import
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
    print("✅ yt-dlp successfully imported")
except ImportError:
    YT_DLP_AVAILABLE = False
    print("❌ yt-dlp not available - falling back to mock mode")

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱
app = FastAPI(
    title="Railway yt-dlp API Server - Fresh Deploy",
    description="Production yt-dlp video extraction service for LinkFetch",
    version="3.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청 모델
class VideoRequest(BaseModel):
    url: HttpUrl
    quality: Optional[str] = "best"

def extract_video_info(url: str) -> Dict[str, Any]:
    """yt-dlp를 사용하여 비디오 정보 추출"""
    if not YT_DLP_AVAILABLE:
        # Mock 데이터 반환
        return {
            "title": "Test Video - Mock Mode",
            "duration": 180,
            "view_count": 1000,
            "uploader": "Test Channel",
            "formats": [
                {"format_id": "18", "ext": "mp4", "height": 360},
                {"format_id": "22", "ext": "mp4", "height": 720}
            ],
            "url": "https://mock-download-url.com/test-video.mp4"
        }
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[height<=720]/best',
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return {
                "title": info.get('title', 'Unknown Title'),
                "duration": info.get('duration'),
                "view_count": info.get('view_count'),
                "uploader": info.get('uploader', 'Unknown'),
                "formats": info.get('formats', [])[:3],  # 상위 3개만
                "url": info.get('url', '')
            }
            
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Video extraction failed: {str(e)}")

@app.get("/")
async def root():
    """메인 엔드포인트"""
    return {
        "message": "🚀 Railway yt-dlp API Server - Fresh Deploy",
        "status": "running",
        "yt_dlp_available": YT_DLP_AVAILABLE,
        "platform": "Railway + Python FastAPI + yt-dlp",
        "version": "3.0.0 - Fresh",
        "port": os.getenv("PORT", "default"),
        "timestamp": int(time.time() * 1000)
    }

@app.get("/health")
async def health():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": int(time.time() * 1000),
        "yt_dlp_status": "available" if YT_DLP_AVAILABLE else "mock_mode",
        "message": "✅ Railway yt-dlp API Server (Fresh Deploy) 정상 동작 중"
    }

@app.post("/extract")
async def extract_video(request: VideoRequest):
    """비디오 정보 추출 (LinkFetch 호환)"""
    try:
        url = str(request.url)
        logger.info(f"📹 Extracting video info: {url}")
        
        video_data = extract_video_info(url)
        
        return {
            "success": True,
            "video_info": {
                "title": video_data["title"],
                "duration": video_data.get("duration"),
                "view_count": video_data.get("view_count"),
                "uploader": video_data.get("uploader"),
                "formats": video_data.get("formats", [])
            },
            "download_url": video_data.get("url", ""),
            "message": "Video information extracted successfully (Fresh Deploy)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Video extraction failed"
        }

@app.get("/status")
async def server_status():
    """서버 상태 정보"""
    return {
        "server": "Railway yt-dlp API - Fresh Deploy",
        "status": "operational",
        "yt_dlp_version": getattr(yt_dlp, "__version__", "unknown") if YT_DLP_AVAILABLE else "not_installed",
        "environment": {
            "PORT": os.getenv("PORT"),
            "RAILWAY_ENVIRONMENT": os.getenv("RAILWAY_ENVIRONMENT")
        }
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    
    logger.info(f"🚀 Railway yt-dlp API Server (Fresh Deploy) 시작")
    logger.info(f"📡 포트: {port}")
    logger.info(f"🎬 yt-dlp 상태: {'Available' if YT_DLP_AVAILABLE else 'Mock Mode'}")
    
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=port,
        reload=False,
        access_log=True
    )