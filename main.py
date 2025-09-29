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
from fastapi.responses import RedirectResponse
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
    """yt-dlp를 사용하여 비디오 정보 및 실제 다운로드 URL 추출"""
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
            "url": "https://mock-download-url.com/test-video.mp4",
            "direct_url": "https://mock-download-url.com/test-video.mp4"
        }
    
    try:
        # 실제 다운로드 가능한 비디오 포맷 선택 (720p 이하, mp4 우선)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': '(mp4)[height<=720]/best[height<=720]/best',
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # 실제 다운로드 가능한 URL 찾기
            download_url = ""
            selected_format = None
            
            # 선택된 포맷 찾기 (yt-dlp가 자동으로 선택한 최적 포맷)
            if 'url' in info and info['url']:
                download_url = info['url']
                
            # formats에서 mp4 포맷 찾기 (백업용)
            if not download_url and 'formats' in info:
                for fmt in info['formats']:
                    if (fmt.get('ext') == 'mp4' and 
                        fmt.get('height', 0) <= 720 and 
                        fmt.get('url')):
                        download_url = fmt['url']
                        selected_format = fmt
                        break
                
                # mp4를 못 찾았으면 다른 형식이라도
                if not download_url:
                    for fmt in info['formats']:
                        if (fmt.get('height', 0) <= 720 and 
                            fmt.get('url') and 
                            fmt.get('vcodec') != 'none'):
                            download_url = fmt['url']
                            selected_format = fmt
                            break
            
            # 포맷 정보 정리 (사용자에게 보여줄 용도)
            processed_formats = []
            if 'formats' in info:
                for fmt in info['formats'][:5]:  # 상위 5개만
                    if fmt.get('vcodec') != 'none' and fmt.get('url'):
                        processed_formats.append({
                            "format_id": fmt.get('format_id', ''),
                            "ext": fmt.get('ext', ''),
                            "height": fmt.get('height'),
                            "filesize": fmt.get('filesize'),
                            "note": fmt.get('format_note', '')
                        })
            
            return {
                "title": info.get('title', 'Unknown Title'),
                "duration": info.get('duration'),
                "view_count": info.get('view_count'),
                "uploader": info.get('uploader', 'Unknown'),
                "formats": processed_formats,
                "url": download_url,  # 실제 다운로드 가능한 URL
                "direct_url": download_url,  # 명시적으로 다운로드 URL
                "selected_format": selected_format.get('format_note', 'auto') if selected_format else 'auto'
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
        
        # Railway 프록시 다운로드 URL 생성
        base_url = "https://railway-ytdlp-fresh-railway-ytdlp-fresh.up.railway.app"
        proxy_url = f"{base_url}/stream?url={url}"
        
        return {
            "success": True,
            "video_info": {
                "title": video_data["title"],
                "duration": video_data.get("duration"),
                "view_count": video_data.get("view_count"),
                "uploader": video_data.get("uploader"),
                "formats": video_data.get("formats", [])
            },
            "download_url": proxy_url,  # Railway 프록시 URL 사용
            "direct_url": proxy_url,
            "proxy_url": proxy_url,
            "selected_format": video_data.get("selected_format", "auto"),
            "message": "Video information extracted with Railway proxy download URL"
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

@app.get("/test-stream")
async def test_stream():
    """스트리밍 테스트 엔드포인트"""
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        if not YT_DLP_AVAILABLE:
            return {"error": "yt-dlp not available"}
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[height<=480][ext=mp4]/best[height<=480]',
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
            
            return {
                "status": "success",
                "title": info.get('title'),
                "has_url": bool(info.get('url')),
                "url_preview": info.get('url', '')[:100] + "..." if info.get('url') else "No URL",
                "format_selected": info.get('format_id'),
                "ext": info.get('ext')
            }
            
    except Exception as e:
        return {"error": str(e)}

@app.get("/stream")
async def stream_video(url: str):
    """비디오 스트리밍/다운로드 - Railway 서버가 프록시 역할 (최적화됨)"""
    try:
        logger.info(f"🎬 Fast streaming request for: {url[:50]}...")
        
        if not YT_DLP_AVAILABLE:
            logger.error("yt-dlp not available")
            raise HTTPException(status_code=503, detail="yt-dlp service not available")
        
        # 최적화된 yt-dlp 옵션 (빠른 추출을 위해)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'worst[height<=480]/worst',  # 빠른 추출을 위해 낮은 품질 먼저 시도
            'noplaylist': True,
            'extract_flat': False,
            'no_check_certificate': True,
            'socket_timeout': 10,  # 10초 타임아웃
        }
        
        logger.info("Fast extracting with optimized yt-dlp...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 타임아웃 방지를 위한 빠른 추출
            info = ydl.extract_info(url, download=False)
            
            # 스트리밍 가능한 URL 찾기
            stream_url = None
            if 'url' in info and info['url']:
                stream_url = info['url']
                logger.info(f"✅ Fast stream URL found: {stream_url[:50]}...")
            
            if not stream_url:
                # 대안 URL 찾기
                if 'formats' in info and info['formats']:
                    for fmt in info['formats'][:3]:  # 처음 3개만 확인
                        if fmt.get('url'):
                            stream_url = fmt['url']
                            logger.info(f"✅ Alternative stream URL found")
                            break
            
            if not stream_url:
                logger.error("❌ No streamable URL found")
                raise HTTPException(status_code=404, detail="No streamable URL found for this video")
            
            # 간단하고 안전한 파일명 생성 (ASCII만 사용)
            timestamp = int(time.time())
            ext = info.get('ext', 'mp4')
            filename = f"video_{timestamp}.{ext}"
            
            logger.info(f"✅ Generated safe filename: {filename}")
            
            # 302 리다이렉트로 실제 비디오 URL로 전달
            response = RedirectResponse(url=stream_url, status_code=302)
            response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
            response.headers["X-Railway-Status"] = "success"
            
            logger.info("✅ Fast redirect to stream URL completed")
            return response
            
    except UnicodeEncodeError as e:
        logger.error(f"Unicode encoding error: {str(e)}")
        return {"error": f"Character encoding error: {str(e)}"}
    except Exception as e:
        logger.error(f"Streaming failed: {str(e)}")
        return {"error": f"Streaming failed: {str(e)}"}

@app.post("/download")
async def prepare_download(request: VideoRequest):
    """다운로드 준비 - 프록시 다운로드 URL 제공"""
    try:
        url = str(request.url)
        # Railway 서버를 통한 프록시 다운로드 URL 생성
        base_url = "https://railway-ytdlp-fresh-railway-ytdlp-fresh.up.railway.app"
        proxy_url = f"{base_url}/stream?url={url}"
        
        return {
            "success": True,
            "download_ready": True,
            "proxy_download_url": proxy_url,
            "direct_url": proxy_url,
            "message": "Railway 프록시 다운로드 URL이 준비되었습니다"
        }
        
    except Exception as e:
        logger.error(f"Download preparation failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Download preparation failed"
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