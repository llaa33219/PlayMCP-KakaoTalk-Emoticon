"""
카카오톡 이모티콘 사양 상수 정의
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class EmoticonType(str, Enum):
    """이모티콘 타입 (AI가 이 enum 값들 중 하나를 선택해야 함)"""
    STATIC = "static"  # 멈춰있는 이모티콘 (32개)
    DYNAMIC = "dynamic"  # 움직이는 이모티콘 (24개)
    BIG = "big"  # 큰 이모티콘 (16개)
    STATIC_MINI = "static-mini"  # 멈춰있는 미니 이모티콘 (42개)
    DYNAMIC_MINI = "dynamic-mini"  # 움직이는 미니 이모티콘 (35개)


class FileExtension(str, Enum):
    """파일 확장자"""
    PNG = "png"
    WEBP = "webp"


class FileType(str, Enum):
    """파일 형식"""
    PNG = "PNG"
    WEBP = "WebP"


@dataclass
class EmoticonSpec:
    """이모티콘 타입별 사양"""
    type: EmoticonType
    count: int  # 이모티콘 개수
    format: str  # 파일 형식 (PNG, WebP)
    sizes: List[Tuple[int, int]]  # 가능한 크기들 (width, height)
    max_size_kb: int  # 최대 파일 크기 (KB)
    icon_size: Tuple[int, int]  # 아이콘 크기
    icon_max_size_kb: int  # 아이콘 최대 크기 (KB)
    is_animated: bool  # 애니메이션 여부


# 이모티콘 타입별 사양 정의
EMOTICON_SPECS: dict[EmoticonType, EmoticonSpec] = {
    EmoticonType.STATIC: EmoticonSpec(
        type=EmoticonType.STATIC,
        count=32,
        format="PNG",
        sizes=[(360, 360)],
        max_size_kb=150,
        icon_size=(78, 78),
        icon_max_size_kb=16,
        is_animated=False,
    ),
    EmoticonType.DYNAMIC: EmoticonSpec(
        type=EmoticonType.DYNAMIC,
        count=24,
        format="WebP",
        sizes=[(360, 360)],
        max_size_kb=650,
        icon_size=(78, 78),
        icon_max_size_kb=16,
        is_animated=True,
    ),
    EmoticonType.BIG: EmoticonSpec(
        type=EmoticonType.BIG,
        count=16,
        format="WebP",
        sizes=[(540, 540), (300, 540), (540, 300)],
        max_size_kb=1024,  # 1MB
        icon_size=(78, 78),
        icon_max_size_kb=16,
        is_animated=True,
    ),
    EmoticonType.STATIC_MINI: EmoticonSpec(
        type=EmoticonType.STATIC_MINI,
        count=42,
        format="PNG",
        sizes=[(180, 180)],
        max_size_kb=100,
        icon_size=(78, 78),
        icon_max_size_kb=16,
        is_animated=False,
    ),
    EmoticonType.DYNAMIC_MINI: EmoticonSpec(
        type=EmoticonType.DYNAMIC_MINI,
        count=35,
        format="WebP",
        sizes=[(180, 180)],
        max_size_kb=500,
        icon_size=(78, 78),
        icon_max_size_kb=16,
        is_animated=True,
    ),
}


# 이모티콘 타입 한글명
EMOTICON_TYPE_NAMES: dict[EmoticonType, str] = {
    EmoticonType.STATIC: "멈춰있는 이모티콘",
    EmoticonType.DYNAMIC: "움직이는 이모티콘",
    EmoticonType.BIG: "큰 이모티콘",
    EmoticonType.STATIC_MINI: "멈춰있는 미니 이모티콘",
    EmoticonType.DYNAMIC_MINI: "움직이는 미니 이모티콘",
}


def get_emoticon_spec(emoticon_type: EmoticonType | str) -> EmoticonSpec:
    """이모티콘 타입에 해당하는 사양을 반환합니다."""
    if isinstance(emoticon_type, str):
        emoticon_type = EmoticonType(emoticon_type)
    return EMOTICON_SPECS[emoticon_type]
