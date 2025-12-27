"""
MCP 요청/응답을 위한 Pydantic 모델 정의
"""
from typing import Optional, List, Union
from pydantic import BaseModel, Field
from src.constants import EmoticonType, FileType, FileExtension


class EmoticonPlan(BaseModel):
    """개별 이모티콘 기획"""
    description: str = Field(..., description="이모티콘 설명 (예: '손 흔드는 고양이', '화난 고양이')")
    file_type: FileType = Field(..., description="파일 형식 (PNG 또는 WebP)")


class BeforePreviewRequest(BaseModel):
    """before-preview 요청 모델"""
    emoticon_type: EmoticonType = Field(..., description="이모티콘 타입")
    title: str = Field(..., description="이모티콘 제목")
    plans: List[EmoticonPlan] = Field(..., description="각 이모티콘별 기획 목록")


class BeforePreviewResponse(BaseModel):
    """before-preview 응답 모델"""
    preview_url: str = Field(..., description="프리뷰 페이지 URL")
    emoticon_type: Union[EmoticonType, str] = Field(..., description="이모티콘 타입")
    title: str
    total_count: int = Field(..., description="계획된 이모티콘 총 개수")


class EmoticonGenerateItem(BaseModel):
    """개별 이모티콘 생성 요청"""
    description: str = Field(..., description="이모티콘 상황/표정/포즈 설명 (예: '신나서 점프하는 고양이', '자는 고양이')")
    file_extension: FileExtension = Field(..., description="파일 확장자 (png 또는 webp)")


class GenerateRequest(BaseModel):
    """generate 요청 모델"""
    emoticon_type: EmoticonType = Field(..., description="이모티콘 타입")
    character_image: Optional[str] = Field(None, description="캐릭터 이미지 (base64 또는 URL)")
    emoticons: List[EmoticonGenerateItem] = Field(..., description="생성할 이모티콘 목록")


class GeneratedEmoticon(BaseModel):
    """생성된 이모티콘 정보"""
    index: int
    image_data: str = Field(..., description="이미지 base64 데이터")
    file_extension: str
    width: int
    height: int
    size_kb: float


class GenerateResponse(BaseModel):
    """generate 응답 모델"""
    emoticons: List[GeneratedEmoticon]
    icon: GeneratedEmoticon = Field(..., description="이모티콘 아이콘")
    emoticon_type: Union[EmoticonType, str] = Field(..., description="이모티콘 타입")


class EmoticonImage(BaseModel):
    """이모티콘 이미지 (after-preview용)"""
    image_data: str = Field(..., description="이미지 base64 또는 URL")
    frames: Optional[List[str]] = Field(None, description="움직이는 이모티콘의 경우 프레임 이미지들")


class AfterPreviewRequest(BaseModel):
    """after-preview 요청 모델"""
    emoticon_type: EmoticonType = Field(..., description="이모티콘 타입")
    title: str = Field(..., description="이모티콘 제목")
    emoticons: List[EmoticonImage] = Field(..., description="이모티콘 이미지 목록")
    icon: Optional[str] = Field(None, description="아이콘 이미지 (base64 또는 URL)")


class AfterPreviewResponse(BaseModel):
    """after-preview 응답 모델"""
    preview_url: str = Field(..., description="프리뷰 페이지 URL")
    download_url: str = Field(..., description="ZIP 다운로드 URL")
    emoticon_type: Union[EmoticonType, str] = Field(..., description="이모티콘 타입")
    title: str


class CheckEmoticonItem(BaseModel):
    """검사할 이모티콘 항목"""
    file_data: str = Field(..., description="파일 데이터 (base64)")
    filename: Optional[str] = Field(None, description="파일명")


class CheckRequest(BaseModel):
    """check 요청 모델"""
    emoticon_type: EmoticonType = Field(..., description="이모티콘 타입")
    emoticons: List[CheckEmoticonItem] = Field(..., description="검사할 이모티콘 목록")
    icon: Optional[CheckEmoticonItem] = Field(None, description="아이콘 이미지")


class CheckIssue(BaseModel):
    """검사 이슈"""
    index: int = Field(..., description="이모티콘 인덱스 (-1: 아이콘, -2: 전체)")
    issue_type: str = Field(..., description="이슈 타입 (size, format, dimension, count)")
    message: str = Field(..., description="이슈 설명")
    current_value: Optional[str] = Field(None, description="현재 값")
    expected_value: Optional[str] = Field(None, description="기대 값")


class CheckResponse(BaseModel):
    """check 응답 모델"""
    is_valid: bool = Field(..., description="모든 검사 통과 여부")
    issues: List[CheckIssue] = Field(default_factory=list, description="발견된 이슈 목록")
    emoticon_type: Union[EmoticonType, str] = Field(..., description="이모티콘 타입")
    checked_count: int = Field(..., description="검사한 이모티콘 개수")
