"""HTTP клиент для работы с API 1С.ai."""

import asyncio
import json
import logging
from typing import Optional, AsyncGenerator, Dict
from datetime import datetime, timedelta

import httpx
from .config import Config
from .models import (
    ConversationRequest, 
    ConversationResponse, 
    MessageRequest,
    MessageChunk,
    ConversationSession,
    ApiError
)

logger = logging.getLogger(__name__)


class OneCApiClient:
    """Клиент для работы с API 1С.ai."""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.base_url.rstrip('/')
        self.sessions: Dict[str, ConversationSession] = {}
        
        # Создаем HTTP клиент
        self.client = httpx.AsyncClient(
            timeout=config.timeout,
            headers={
                "Accept": "*/*",
                "Accept-Charset": "utf-8",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "ru-ru,en-us;q=0.8,en;q=0.7",
                "Authorization": config.onec_ai_token,
                "Content-Type": "application/json; charset=utf-8",
                "Origin": config.base_url,
                "Referer": f"{config.base_url}/chat/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/620.1 (KHTML, like Gecko) JavaFX/22 Safari/620.1",
            }
        )
    
    async def create_conversation(
        self, 
        programming_language: Optional[str] = None,
        script_language: Optional[str] = None
    ) -> str:
        """Создать новую дискуссию."""
        try:
            request_data = ConversationRequest(
                ui_language=self.config.ui_language,
                programming_language=programming_language or self.config.programming_language,
                script_language=script_language or self.config.script_language
            )
            
            response = await self.client.post(
                f"{self.base_url}/chat_api/v1/conversations/",
                json=request_data.dict(),
                headers={"Session-Id": ""}
            )
            
            if response.status_code != 200:
                raise ApiError(
                    f"Ошибка создания дискуссии: {response.status_code}", 
                    response.status_code
                )
            
            conversation_response = ConversationResponse(**response.json())
            conversation_id = conversation_response.uuid
            
            # Сохраняем сессию
            self.sessions[conversation_id] = ConversationSession(
                conversation_id=conversation_id
            )
            
            logger.info(f"Создана новая дискуссия: {conversation_id}")
            return conversation_id
            
        except httpx.RequestError as e:
            raise ApiError(f"Ошибка сети при создании дискуссии: {str(e)}")
        except Exception as e:
            raise ApiError(f"Неожиданная ошибка при создании дискуссии: {str(e)}")
    
    async def send_message(self, conversation_id: str, message: str) -> str:
        """Отправить сообщение в дискуссию и получить ответ."""
        try:
            # Проверяем существование сессии
            if conversation_id not in self.sessions:
                self.sessions[conversation_id] = ConversationSession(
                    conversation_id=conversation_id
                )
            
            # Обновляем использование сессии
            self.sessions[conversation_id].update_usage()
            
            request_data = MessageRequest(instruction=message)
            
            # Отправляем сообщение
            url = f"{self.base_url}/chat_api/v1/conversations/{conversation_id}/messages"
            
            async with self.client.stream(
                "POST",
                url,
                json=request_data.dict(),
                headers={"Accept": "text/event-stream"}
            ) as response:
                
                if response.status_code != 200:
                    raise ApiError(
                        f"Ошибка отправки сообщения: {response.status_code}",
                        response.status_code
                    )
                
                # Собираем ответ из SSE потока
                full_response = await self._parse_sse_response(response)
                
                logger.info(f"Получен ответ для дискуссии {conversation_id}")
                return full_response
                
        except httpx.RequestError as e:
            raise ApiError(f"Ошибка сети при отправке сообщения: {str(e)}")
        except Exception as e:
            raise ApiError(f"Неожиданная ошибка при отправке сообщения: {str(e)}")
    
    async def _parse_sse_response(self, response: httpx.Response) -> str:
        """Парсинг Server-Sent Events ответа."""
        full_text = ""
        
        # Убеждаемся что кодировка UTF-8
        response.encoding = 'utf-8'
        
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                try:
                    data_str = line[6:]  # Убираем "data: "
                    data = json.loads(data_str)
                    
                    chunk = MessageChunk(**data)
                    
                    # Если это ответ ассистента с контентом
                    if (chunk.role == "assistant" and 
                        chunk.content and 
                        "text" in chunk.content):
                        
                        text = chunk.content["text"]
                        if text:
                            # Нормализуем текст для безопасности
                            text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                            full_text = text  # Берем полный текст из последнего чанка
                        
                        # Если сообщение завершено
                        if chunk.finished:
                            break
                            
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.warning(f"Ошибка парсинга SSE chunk: {e}")
                    continue
        
        return full_text.strip()
    
    async def get_or_create_session(
        self, 
        create_new: bool = False,
        programming_language: Optional[str] = None
    ) -> str:
        """Получить существующую сессию или создать новую."""
        
        # Очищаем устаревшие сессии
        await self._cleanup_old_sessions()
        
        # Если требуется новая сессия или нет активных сессий
        if create_new or not self.sessions:
            return await self.create_conversation(programming_language)
        
        # Проверяем лимит активных сессий
        if len(self.sessions) >= self.config.max_active_sessions:
            # Удаляем самую старую сессию
            oldest_session_id = min(
                self.sessions.keys(), 
                key=lambda k: self.sessions[k].last_used
            )
            del self.sessions[oldest_session_id]
            logger.info(f"Удалена старая сессия: {oldest_session_id}")
        
        # Возвращаем самую свежую сессию
        recent_session_id = max(
            self.sessions.keys(), 
            key=lambda k: self.sessions[k].last_used
        )
        
        return recent_session_id
    
    async def _cleanup_old_sessions(self):
        """Очистка устаревших сессий."""
        current_time = datetime.now()
        ttl_delta = timedelta(seconds=self.config.session_ttl)
        
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if current_time - session.last_used > ttl_delta
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"Удалена устаревшая сессия: {session_id}")
    
    async def close(self):
        """Закрыть HTTP клиент."""
        await self.client.aclose()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close() 