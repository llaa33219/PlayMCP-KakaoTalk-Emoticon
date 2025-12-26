"""
카카오톡 이모티콘 사양 상수 정의
"""
from dataclasses import dataclass
from typing import Literal, List, Tuple

EmoticonType = Literal["static", "dynamic", "big", "static-mini", "dynamic-mini"]


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
    "static": EmoticonSpec(
        type="static",
        count=32,
        format="PNG",
        sizes=[(360, 360)],
        max_size_kb=150,
        icon_size=(78, 78),
        icon_max_size_kb=16,
        is_animated=False,
    ),
    "dynamic": EmoticonSpec(
        type="dynamic",
        count=24,
        format="WebP",
        sizes=[(360, 360)],
        max_size_kb=650,
        icon_size=(78, 78),
        icon_max_size_kb=16,
        is_animated=True,
    ),
    "big": EmoticonSpec(
        type="big",
        count=16,
        format="WebP",
        sizes=[(540, 540), (300, 540), (540, 300)],
        max_size_kb=1024,  # 1MB
        icon_size=(78, 78),
        icon_max_size_kb=16,
        is_animated=True,
    ),
    "static-mini": EmoticonSpec(
        type="static-mini",
        count=42,
        format="PNG",
        sizes=[(180, 180)],
        max_size_kb=100,
        icon_size=(78, 78),
        icon_max_size_kb=16,
        is_animated=False,
    ),
    "dynamic-mini": EmoticonSpec(
        type="dynamic-mini",
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
    "static": "멈춰있는 이모티콘",
    "dynamic": "움직이는 이모티콘",
    "big": "큰 이모티콘",
    "static-mini": "멈춰있는 미니 이모티콘",
    "dynamic-mini": "움직이는 미니 이모티콘",
}
