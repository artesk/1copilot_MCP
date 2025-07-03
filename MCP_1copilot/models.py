"""Pydantic модели для API 1С.ai и MCP."""

from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field
from datetime import datetime


class ConversationRequest(BaseModel):
    """Запрос на создание новой дискуссии."""
    tool_name: str = "custom"
    ui_language: str = "russian"
    programming_language: str = ""
    script_language: str = ""


class ConversationResponse(BaseModel):
    """Ответ при создании дискуссии."""
    uuid: str


class MessageRequest(BaseModel):
    """Запрос на отправку сообщения в дискуссию."""
    parent_uuid: Optional[str] = None
    tool_content: Dict[str, str] = Field(default_factory=dict)
    
    def __init__(self, instruction: str, **kwargs):
        super().__init__(**kwargs)
        self.tool_content = {"instruction": instruction}


class MessageChunk(BaseModel):
    """Часть сообщения из SSE потока."""
    uuid: str
    role: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    parent_uuid: Optional[str] = None
    create_time: Optional[str] = None
    finished: bool = False


class ConversationSession(BaseModel):
    """Сессия дискуссии."""
    conversation_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    last_used: datetime = Field(default_factory=datetime.now)
    messages_count: int = 0
    
    def update_usage(self):
        """Обновить время последнего использования."""
        self.last_used = datetime.now()
        self.messages_count += 1


class ApiError(Exception):
    """Ошибка API 1С.ai."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class McpToolRequest(BaseModel):
    """Запрос к MCP инструменту."""
    question: str = Field(..., description="Вопрос для модели 1С.ai")
    programming_language: Optional[str] = Field(
        default=None, 
        description="Язык программирования (опционально)"
    )
    create_new_session: bool = Field(
        default=False, 
        description="Создать новую сессию"
    )


class McpToolResponse(BaseModel):
    """Ответ от MCP инструмента."""
    answer: str = Field(..., description="Ответ от модели 1С.ai")
    conversation_id: str = Field(..., description="ID дискуссии")
    success: bool = True
    error: Optional[str] = None 