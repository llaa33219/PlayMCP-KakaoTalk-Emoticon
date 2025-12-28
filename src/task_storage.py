"""
비동기 이미지 생성 작업 관리 모듈
"""
import asyncio
import secrets
import string
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field


class TaskStatus(str, Enum):
    """작업 상태"""
    PENDING = "pending"       # 대기 중
    RUNNING = "running"       # 실행 중
    COMPLETED = "completed"   # 완료
    FAILED = "failed"         # 실패


@dataclass
class GenerationTask:
    """이미지 생성 작업"""
    task_id: str
    status: TaskStatus
    emoticon_type: str
    total_count: int
    completed_count: int = 0
    current_description: str = ""
    emoticons: List[Dict[str, Any]] = field(default_factory=list)
    icon: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "emoticon_type": self.emoticon_type,
            "total_count": self.total_count,
            "completed_count": self.completed_count,
            "current_description": self.current_description,
            "progress_percent": round((self.completed_count / self.total_count) * 100) if self.total_count > 0 else 0,
            "emoticons": self.emoticons,
            "icon": self.icon,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class TaskStorage:
    """작업 저장소"""
    
    # 최대 작업 저장 개수 (오래된 것부터 삭제)
    MAX_TASKS = 100
    
    def __init__(self):
        self._tasks: Dict[str, GenerationTask] = {}
        self._lock = asyncio.Lock()
    
    async def _cleanup_old_tasks(self) -> None:
        """오래된 작업 정리 (MAX_TASKS 초과 시)"""
        if len(self._tasks) > self.MAX_TASKS:
            # created_at 기준으로 정렬하여 오래된 것부터 삭제
            sorted_tasks = sorted(
                self._tasks.items(),
                key=lambda x: x[1].created_at
            )
            # 가장 오래된 작업들 삭제 (절반 정리)
            tasks_to_remove = sorted_tasks[:len(sorted_tasks) // 2]
            for task_id, _ in tasks_to_remove:
                del self._tasks[task_id]
    
    def _generate_task_id(self, length: int = 12) -> str:
        """짧은 랜덤 작업 ID 생성"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    async def create_task(self, emoticon_type: str, total_count: int) -> GenerationTask:
        """새 작업 생성"""
        async with self._lock:
            # 오래된 작업 정리
            await self._cleanup_old_tasks()
            
            task_id = self._generate_task_id()
            task = GenerationTask(
                task_id=task_id,
                status=TaskStatus.PENDING,
                emoticon_type=emoticon_type,
                total_count=total_count
            )
            self._tasks[task_id] = task
            return task
    
    async def get_task(self, task_id: str) -> Optional[GenerationTask]:
        """작업 조회"""
        return self._tasks.get(task_id)
    
    async def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """작업 상태 업데이트"""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = status
                self._tasks[task_id].updated_at = datetime.now()
    
    async def update_task_progress(
        self, 
        task_id: str, 
        completed_count: int, 
        current_description: str = ""
    ) -> None:
        """작업 진행 상황 업데이트"""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].completed_count = completed_count
                self._tasks[task_id].current_description = current_description
                self._tasks[task_id].updated_at = datetime.now()
    
    async def add_emoticon(self, task_id: str, emoticon: Dict[str, Any]) -> None:
        """생성된 이모티콘 추가"""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].emoticons.append(emoticon)
                self._tasks[task_id].updated_at = datetime.now()
    
    async def set_icon(self, task_id: str, icon: Dict[str, Any]) -> None:
        """아이콘 설정"""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].icon = icon
                self._tasks[task_id].updated_at = datetime.now()
    
    async def set_error(self, task_id: str, error_message: str) -> None:
        """에러 설정"""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.FAILED
                self._tasks[task_id].error_message = error_message
                self._tasks[task_id].updated_at = datetime.now()
    
    async def complete_task(self, task_id: str) -> None:
        """작업 완료"""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.COMPLETED
                self._tasks[task_id].updated_at = datetime.now()


# 전역 인스턴스
_task_storage: Optional[TaskStorage] = None


def get_task_storage() -> TaskStorage:
    """작업 저장소 인스턴스 반환"""
    global _task_storage
    if _task_storage is None:
        _task_storage = TaskStorage()
    return _task_storage
