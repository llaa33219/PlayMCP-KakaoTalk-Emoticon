"""
MCP 도구 구현
"""
import os
from typing import List, Optional

from src.constants import EMOTICON_SPECS, EMOTICON_TYPE_NAMES, EmoticonType
from src.models import (
    BeforePreviewRequest, BeforePreviewResponse,
    GenerateRequest, GenerateResponse, GeneratedEmoticon,
    AfterPreviewRequest, AfterPreviewResponse,
    CheckRequest, CheckResponse, CheckIssue
)
from src.preview_generator import get_preview_generator
from src.checker import get_checker
from src.image_utils import (
    get_image_bytes, encode_base64_image, get_image_info,
    process_emoticon_image, create_icon, video_to_animated_webp,
    decode_base64_image
)
from src.huggingface_client import get_hf_client


async def before_preview(request: BeforePreviewRequest) -> BeforePreviewResponse:
    """
    이모티콘 제작 이전 프리뷰
    
    카카오톡 채팅방과 같은 디자인의 페이지에서 이모티콘 탭 부분에
    이모티콘 설명이 글자로 써있는 형태의 프리뷰 페이지 URL을 반환합니다.
    """
    generator = get_preview_generator(os.environ.get("BASE_URL", ""))
    
    plans = [
        {"description": plan.description, "file_type": plan.file_type}
        for plan in request.plans
    ]
    
    preview_url = generator.generate_before_preview(
        emoticon_type=request.emoticon_type,
        title=request.title,
        plans=plans
    )
    
    return BeforePreviewResponse(
        preview_url=preview_url,
        emoticon_type=request.emoticon_type,
        title=request.title,
        total_count=len(request.plans)
    )


async def generate(
    request: GenerateRequest,
    hf_token: Optional[str] = None
) -> GenerateResponse:
    """
    이모티콘 생성
    
    캐릭터 이미지와 이모티콘 설명을 기반으로 이모티콘을 생성합니다.
    캐릭터 이미지가 없으면 먼저 캐릭터를 생성합니다.
    움직이는 이모티콘은 비디오를 생성한 후 WebP로 변환합니다.
    """
    spec = EMOTICON_SPECS[request.emoticon_type]
    hf_client = get_hf_client(hf_token)
    
    # 캐릭터 이미지 준비
    if request.character_image:
        character_bytes = await get_image_bytes(request.character_image)
    else:
        # 캐릭터 이미지가 없으면 기본 캐릭터 생성
        character_bytes = await hf_client.generate_character(
            "A cute cartoon character with simple design, white background, "
            "suitable for emoticon/sticker, kawaii style"
        )
    
    generated_emoticons: List[GeneratedEmoticon] = []
    
    for idx, emoticon_item in enumerate(request.emoticons):
        # 이모티콘 생성
        is_animated = spec.is_animated
        
        if is_animated:
            # 움직이는 이모티콘: 비디오 생성 후 WebP 변환
            video_bytes = await hf_client.generate_emoticon(
                character_image=character_bytes,
                emoticon_description=emoticon_item.description,
                is_animated=True,
                animation_prompt=emoticon_item.description
            )
            
            # 비디오를 애니메이션 WebP로 변환
            image_bytes = video_to_animated_webp(
                video_bytes,
                output_size=spec.sizes[0],
                max_size_kb=spec.max_size_kb,
                fps=15
            )
            mime_type = "image/webp"
        else:
            # 멈춰있는 이모티콘: 이미지 생성
            raw_image = await hf_client.generate_emoticon(
                character_image=character_bytes,
                emoticon_description=emoticon_item.description,
                is_animated=False
            )
            
            # 사양에 맞게 이미지 처리
            image_bytes = process_emoticon_image(raw_image, spec)
            mime_type = "image/png" if spec.format == "PNG" else "image/webp"
        
        width, height, _ = get_image_info(image_bytes)
        size_kb = len(image_bytes) / 1024
        
        generated_emoticons.append(GeneratedEmoticon(
            index=idx,
            image_data=encode_base64_image(image_bytes, mime_type),
            file_extension=emoticon_item.file_extension,
            width=width,
            height=height,
            size_kb=round(size_kb, 2)
        ))
    
    # 아이콘 생성 (첫 번째 이모티콘 기반)
    if generated_emoticons:
        first_emoticon_data = generated_emoticons[0].image_data
        first_emoticon_bytes = decode_base64_image(first_emoticon_data)
        icon_bytes = create_icon(first_emoticon_bytes, spec)
    else:
        icon_bytes = create_icon(character_bytes, spec)
    
    icon_width, icon_height, _ = get_image_info(icon_bytes)
    icon = GeneratedEmoticon(
        index=-1,
        image_data=encode_base64_image(icon_bytes, "image/png"),
        file_extension="png",
        width=icon_width,
        height=icon_height,
        size_kb=round(len(icon_bytes) / 1024, 2)
    )
    
    return GenerateResponse(
        emoticons=generated_emoticons,
        icon=icon,
        emoticon_type=request.emoticon_type
    )


async def after_preview(request: AfterPreviewRequest) -> AfterPreviewResponse:
    """
    완성본 프리뷰
    
    실제 이모티콘 이미지가 포함된 프리뷰 페이지 URL과
    ZIP 다운로드 URL을 반환합니다.
    """
    generator = get_preview_generator(os.environ.get("BASE_URL", ""))
    
    emoticons = [
        {"image_data": emoticon.image_data, "frames": emoticon.frames}
        for emoticon in request.emoticons
    ]
    
    preview_url, download_url = generator.generate_after_preview(
        emoticon_type=request.emoticon_type,
        title=request.title,
        emoticons=emoticons,
        icon=request.icon
    )
    
    return AfterPreviewResponse(
        preview_url=preview_url,
        download_url=download_url,
        emoticon_type=request.emoticon_type,
        title=request.title
    )


async def check(request: CheckRequest) -> CheckResponse:
    """
    이모티콘 검사
    
    이모티콘이 카카오톡 사양에 맞는지 검사합니다.
    파일 형식, 크기, 개수 등을 검사합니다.
    """
    checker = get_checker()
    
    # 이미지 바이트로 변환
    emoticon_bytes_list = []
    for emoticon in request.emoticons:
        emoticon_bytes = decode_base64_image(emoticon.file_data)
        emoticon_bytes_list.append(emoticon_bytes)
    
    icon_bytes = None
    if request.icon:
        icon_bytes = decode_base64_image(request.icon.file_data)
    
    is_valid, issues = checker.check_emoticons(
        emoticon_type=request.emoticon_type,
        emoticons=emoticon_bytes_list,
        icon=icon_bytes
    )
    
    return CheckResponse(
        is_valid=is_valid,
        issues=issues,
        emoticon_type=request.emoticon_type,
        checked_count=len(request.emoticons)
    )
