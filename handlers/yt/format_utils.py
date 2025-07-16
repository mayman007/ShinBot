import os
import asyncio
import yt_dlp
from typing import Dict, List, Optional, Any, Tuple
from .constants import COOKIES_FILE

def add_cookies_to_opts(opts: dict) -> dict:
    """Add cookies to yt-dlp options if cookie file exists."""
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
    if 'restrictfilenames' not in opts:
        opts['restrictfilenames'] = True
    return opts

async def extract_info(url: str, download: bool = False) -> Dict[str, Any]:
    """Extract video info using yt-dlp with error handling."""
    try:
        with yt_dlp.YoutubeDL(add_cookies_to_opts({'quiet': True})) as ydl:
            return await asyncio.to_thread(ydl.extract_info, url, download)
    except yt_dlp.utils.DownloadError as e:
        raise ValueError(f"Error extracting video info: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error: {str(e)}")

def get_best_audio(info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get the best audio format from video info."""
    if not info:
        return None
    
    audio_formats = [
        fmt for fmt in info.get('formats', [])
        if fmt.get('vcodec') == 'none' and (fmt.get('filesize') or fmt.get('filesize_approx'))
    ]
    
    return max(audio_formats, key=lambda f: f.get('filesize') or f.get('filesize_approx'), default=None) if audio_formats else None

def get_resolution(fmt: Dict[str, Any]) -> str:
    """Get formatted resolution string from format info."""
    if fmt.get('resolution'):
        return fmt['resolution']
    elif fmt.get('height'):
        return f"{fmt['height']}p"
    else:
        return "N/A"

def get_size(fmt: Dict[str, Any]) -> Optional[int]:
    """Get size from format info in bytes."""
    return fmt.get('filesize') or fmt.get('filesize_approx')

async def list_video_options(url: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """List available video formats with sizes and resolutions."""
    info = await extract_info(url)
    best_audio = get_best_audio(info)
    
    candidates = []
    for fmt in info.get('formats', []):
        # Accept both mp4 and other formats, but prioritize mp4
        if fmt.get('vcodec') == 'none':
            continue
            
        # Skip formats that are known to be problematic
        if fmt.get('format_note') and 'av01' in fmt.get('format_note', '').lower():
            continue  # Skip AV1 codec which has compatibility issues
            
        resolution = get_resolution(fmt)
        video_size = get_size(fmt)
        
        if video_size is None:
            continue
            
        # Prefer mp4 container and h264 codec
        container_score = 2 if fmt.get('ext') == 'mp4' else 1
        codec_score = 2 if fmt.get('vcodec', '').startswith('avc1') or 'h264' in fmt.get('vcodec', '') else 1
        compatibility_score = container_score + codec_score
        
        if fmt.get('acodec') != 'none':
            total_size = video_size
            stream_type = "Progressive"
        else:
            stream_type = "Adaptive"
            audio_size = get_size(best_audio) if best_audio else None
            total_size = video_size + audio_size if audio_size is not None else video_size
            
        candidates.append({
            'format': fmt,
            'resolution': resolution,
            'stream_type': stream_type,
            'video_size': video_size,
            'total_size': total_size,
            'compatibility_score': compatibility_score,
        })
    
    # Group by resolution and select best quality for each, prioritizing compatibility
    grouped = {}
    for cand in candidates:
        res = cand['resolution']
        if res in grouped:
            existing = grouped[res]
            # Prefer higher compatibility score, then larger size
            if (cand['compatibility_score'] > existing['compatibility_score'] or
                (cand['compatibility_score'] == existing['compatibility_score'] and
                 cand['total_size'] is not None and existing['total_size'] is not None and
                 cand['total_size'] > existing['total_size'])):
                grouped[res] = cand
            elif cand['total_size'] is not None and existing['total_size'] is None:
                grouped[res] = cand
        else:
            grouped[res] = cand
    
    video_options = list(grouped.values())
    # Sort by height for consistent order
    video_options.sort(key=lambda c: int(c['format'].get('height') or 0))
    
    return info, video_options, best_audio

async def list_audio_options(url: str) -> List[Dict[str, Any]]:
    """List available audio formats with bitrates and sizes."""
    info = await extract_info(url)
    
    audio_candidates = []
    for fmt in info.get("formats", []):
        if fmt.get("vcodec") != "none":
            continue
            
        size = fmt.get("filesize") or fmt.get("filesize_approx")
        if not size:
            continue
            
        abr = fmt.get("abr")
        if not abr:
            continue
            
        audio_candidates.append({
            "format": fmt,
            "abr": abr,
            "filesize": size,
        })
    
    # Group by bitrate and select best quality for each
    unique = {}
    for candidate in audio_candidates:
        key = candidate["abr"]
        if key in unique:
            if candidate["filesize"] > unique[key]["filesize"]:
                unique[key] = candidate
        else:
            unique[key] = candidate
    
    options = list(unique.values())
    options.sort(key=lambda c: c["abr"], reverse=True)
    
    return options
