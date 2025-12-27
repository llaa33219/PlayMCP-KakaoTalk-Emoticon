"""
이모티콘 사양 검사 모듈
"""
import io
from typing import List, Optional, Tuple
from PIL import Image

from src.constants import EmoticonType, get_emoticon_spec, EmoticonSpec
from src.image_utils import decode_base64_image
from src.models import CheckIssue


class EmoticonChecker:
    """이모티콘 사양 검사기"""
    
    def check_emoticons(
        self,
        emoticon_type: EmoticonType | str,
        emoticons: List[bytes],
        icon: Optional[bytes] = None
    ) -> Tuple[bool, List[CheckIssue]]:
        """
        이모티콘 사양 검사
        
        Args:
            emoticon_type: 이모티콘 타입 (Enum 또는 문자열)
            emoticons: 이모티콘 이미지 바이트 목록
            icon: 아이콘 이미지 바이트 (선택)
            
        Returns:
            (검사 통과 여부, 이슈 목록) 튜플
        """
        spec = get_emoticon_spec(emoticon_type)
        issues: List[CheckIssue] = []
        
        # 개수 검사
        if len(emoticons) != spec.count:
            issues.append(CheckIssue(
                index=-2,
                issue_type="count",
                message=f"이모티콘 개수가 맞지 않습니다",
                current_value=str(len(emoticons)),
                expected_value=str(spec.count)
            ))
        
        # 각 이모티콘 검사
        for idx, emoticon_bytes in enumerate(emoticons):
            emoticon_issues = self._check_single_emoticon(
                emoticon_bytes, spec, idx
            )
            issues.extend(emoticon_issues)
        
        # 아이콘 검사
        if icon:
            icon_issues = self._check_icon(icon, spec)
            issues.extend(icon_issues)
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def _check_single_emoticon(
        self,
        image_bytes: bytes,
        spec: "EmoticonSpec",
        index: int
    ) -> List[CheckIssue]:
        """단일 이모티콘 검사"""
        issues: List[CheckIssue] = []
        
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                width, height = img.size
                img_format = img.format or "UNKNOWN"
                
                # 파일 형식 검사
                expected_format = spec.format.upper()
                if expected_format == "WEBP" and img_format.upper() != "WEBP":
                    issues.append(CheckIssue(
                        index=index,
                        issue_type="format",
                        message=f"이모티콘 #{index + 1}: 파일 형식이 올바르지 않습니다",
                        current_value=img_format,
                        expected_value=expected_format
                    ))
                elif expected_format == "PNG" and img_format.upper() != "PNG":
                    issues.append(CheckIssue(
                        index=index,
                        issue_type="format",
                        message=f"이모티콘 #{index + 1}: 파일 형식이 올바르지 않습니다",
                        current_value=img_format,
                        expected_value=expected_format
                    ))
                
                # 크기 검사
                valid_size = False
                for valid_width, valid_height in spec.sizes:
                    if width == valid_width and height == valid_height:
                        valid_size = True
                        break
                
                if not valid_size:
                    expected_sizes = ", ".join(
                        f"{w}x{h}" for w, h in spec.sizes
                    )
                    issues.append(CheckIssue(
                        index=index,
                        issue_type="dimension",
                        message=f"이모티콘 #{index + 1}: 이미지 크기가 올바르지 않습니다",
                        current_value=f"{width}x{height}",
                        expected_value=expected_sizes
                    ))
        except Exception as e:
            issues.append(CheckIssue(
                index=index,
                issue_type="format",
                message=f"이모티콘 #{index + 1}: 이미지를 읽을 수 없습니다 - {str(e)}",
                current_value="invalid",
                expected_value=spec.format
            ))
            return issues
        
        # 파일 크기 검사
        size_kb = len(image_bytes) / 1024
        if size_kb > spec.max_size_kb:
            issues.append(CheckIssue(
                index=index,
                issue_type="size",
                message=f"이모티콘 #{index + 1}: 파일 크기가 너무 큽니다",
                current_value=f"{size_kb:.1f} KB",
                expected_value=f"{spec.max_size_kb} KB 이하"
            ))
        
        return issues
    
    def _check_icon(
        self,
        image_bytes: bytes,
        spec: "EmoticonSpec"
    ) -> List[CheckIssue]:
        """아이콘 검사"""
        issues: List[CheckIssue] = []
        
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                width, height = img.size
                img_format = img.format or "UNKNOWN"
                
                # 파일 형식 검사 (아이콘은 항상 PNG)
                if img_format.upper() != "PNG":
                    issues.append(CheckIssue(
                        index=-1,
                        issue_type="format",
                        message="아이콘: 파일 형식이 올바르지 않습니다",
                        current_value=img_format,
                        expected_value="PNG"
                    ))
                
                # 크기 검사
                expected_width, expected_height = spec.icon_size
                if width != expected_width or height != expected_height:
                    issues.append(CheckIssue(
                        index=-1,
                        issue_type="dimension",
                        message="아이콘: 이미지 크기가 올바르지 않습니다",
                        current_value=f"{width}x{height}",
                        expected_value=f"{expected_width}x{expected_height}"
                    ))
        except Exception as e:
            issues.append(CheckIssue(
                index=-1,
                issue_type="format",
                message=f"아이콘: 이미지를 읽을 수 없습니다 - {str(e)}",
                current_value="invalid",
                expected_value="PNG"
            ))
            return issues
        
        # 파일 크기 검사
        size_kb = len(image_bytes) / 1024
        if size_kb > spec.icon_max_size_kb:
            issues.append(CheckIssue(
                index=-1,
                issue_type="size",
                message="아이콘: 파일 크기가 너무 큽니다",
                current_value=f"{size_kb:.1f} KB",
                expected_value=f"{spec.icon_max_size_kb} KB 이하"
            ))
        
        return issues


def get_checker() -> EmoticonChecker:
    """검사기 인스턴스 반환"""
    return EmoticonChecker()
