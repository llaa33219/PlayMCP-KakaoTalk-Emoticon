"""
이미지 처리 유틸리티 함수
"""
import base64
import io
import subprocess
import tempfile
import os
from typing import Tuple, Optional, List
from PIL import Image
import httpx

from src.constants import EmoticonSpec, EMOTICON_SPECS


async def download_image(url: str) -> bytes:
    """URL에서 이미지 다운로드"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def decode_base64_image(data: str) -> bytes:
    """Base64 인코딩된 이미지 디코딩"""
    if data.startswith("data:"):
        data = data.split(",", 1)[1]
    return base64.b64decode(data)


def encode_base64_image(data: bytes, mime_type: str = "image/png") -> str:
    """이미지를 Base64로 인코딩"""
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


async def get_image_bytes(image_data: str) -> bytes:
    """이미지 데이터(URL 또는 base64)에서 바이트 추출"""
    if image_data.startswith("http://") or image_data.startswith("https://"):
        return await download_image(image_data)
    return decode_base64_image(image_data)


def get_image_info(image_bytes: bytes) -> Tuple[int, int, str]:
    """이미지 정보 (width, height, format) 반환"""
    with Image.open(io.BytesIO(image_bytes)) as img:
        return img.width, img.height, img.format or "UNKNOWN"


def resize_image(
    image_bytes: bytes,
    target_size: Tuple[int, int],
    output_format: str = "PNG"
) -> bytes:
    """이미지 리사이즈"""
    with Image.open(io.BytesIO(image_bytes)) as img:
        if img.mode == "RGBA" and output_format.upper() == "JPEG":
            img = img.convert("RGB")
        
        resized = img.resize(target_size, Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        resized.save(output, format=output_format)
        return output.getvalue()


def compress_image(
    image_bytes: bytes,
    max_size_kb: int,
    output_format: str = "PNG"
) -> bytes:
    """이미지 압축하여 최대 크기 이하로 맞춤"""
    with Image.open(io.BytesIO(image_bytes)) as img:
        output = io.BytesIO()
        
        if output_format.upper() == "PNG":
            img.save(output, format="PNG", optimize=True)
        elif output_format.upper() == "WEBP":
            quality = 90
            while quality > 10:
                output = io.BytesIO()
                img.save(output, format="WEBP", quality=quality)
                if len(output.getvalue()) <= max_size_kb * 1024:
                    break
                quality -= 10
        else:
            img.save(output, format=output_format)
        
        return output.getvalue()


def process_emoticon_image(
    image_bytes: bytes,
    spec: EmoticonSpec,
    target_size: Optional[Tuple[int, int]] = None
) -> bytes:
    """이모티콘 사양에 맞게 이미지 처리"""
    if target_size is None:
        target_size = spec.sizes[0]
    
    resized = resize_image(image_bytes, target_size, spec.format)
    compressed = compress_image(resized, spec.max_size_kb, spec.format)
    
    return compressed


def create_icon(image_bytes: bytes, spec: EmoticonSpec) -> bytes:
    """이모티콘 아이콘 생성"""
    resized = resize_image(image_bytes, spec.icon_size, "PNG")
    compressed = compress_image(resized, spec.icon_max_size_kb, "PNG")
    return compressed


def video_to_animated_webp(
    video_bytes: bytes,
    output_size: Tuple[int, int],
    max_size_kb: int,
    fps: int = 15,
    duration_seconds: float = 2.0
) -> bytes:
    """비디오를 애니메이션 WebP로 변환"""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input.mp4")
        output_path = os.path.join(tmpdir, "output.webp")
        
        with open(video_path, "wb") as f:
            f.write(video_bytes)
        
        result = b""
        quality = 80
        while quality > 10:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-t", str(duration_seconds),
                "-vcodec", "libwebp",
                "-filter:v", f"fps={fps},scale={output_size[0]}:{output_size[1]}",
                "-lossless", "0",
                "-compression_level", "6",
                "-q:v", str(quality),
                "-loop", "0",
                "-preset", "picture",
                "-an",
                "-vsync", "0",
                output_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            with open(output_path, "rb") as f:
                result = f.read()
            
            if len(result) <= max_size_kb * 1024:
                return result
            
            quality -= 10
        
        return result


def frames_to_animated_webp(
    frames: List[bytes],
    output_size: Tuple[int, int],
    max_size_kb: int,
    fps: int = 15
) -> bytes:
    """프레임 이미지들을 애니메이션 WebP로 변환"""
    images = []
    for frame_bytes in frames:
        with Image.open(io.BytesIO(frame_bytes)) as img:
            resized = img.resize(output_size, Image.Resampling.LANCZOS)
            if resized.mode != "RGBA":
                resized = resized.convert("RGBA")
            images.append(resized.copy())
    
    if not images:
        raise ValueError("No frames provided")
    
    duration = int(1000 / fps)  # 밀리초
    
    output = io.BytesIO()
    images[0].save(
        output,
        format="WEBP",
        save_all=True,
        append_images=images[1:],
        duration=duration,
        loop=0,
        quality=80
    )
    
    result = output.getvalue()
    
    if len(result) > max_size_kb * 1024:
        quality = 70
        while quality > 10 and len(result) > max_size_kb * 1024:
            output = io.BytesIO()
            images[0].save(
                output,
                format="WEBP",
                save_all=True,
                append_images=images[1:],
                duration=duration,
                loop=0,
                quality=quality
            )
            result = output.getvalue()
            quality -= 10
    
    return result
