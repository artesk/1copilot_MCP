"""Основной MCP сервер для интеграции с 1С.ai."""

import asyncio
import logging
from typing import Any, Sequence, Optional

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource, 
    Tool, 
    TextContent, 
    ImageContent, 
    EmbeddedResource,
    LoggingLevel
)
import mcp.types as types

from .config import get_config, Config
from .api_client import OneCApiClient
from .models import ApiError, McpToolRequest, McpToolResponse

# Настройка логирования только для ошибок при работе с MCP
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


class OneCMcpServer:
    """MCP сервер для интеграции с 1С.ai."""
    
    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Очистка текста от проблемных символов для корректного отображения."""
        if not text:
            return text
        
        # Удаляем или заменяем проблемные Unicode символы
        import unicodedata
        
        # Нормализуем Unicode
        text = unicodedata.normalize('NFKC', text)
        
        # Удаляем управляющие символы кроме стандартных переносов строк
        cleaned = ''
        for char in text:
            if unicodedata.category(char) not in ['Cc', 'Cf'] or char in ['\n', '\r', '\t']:
                cleaned += char
            
        return cleaned
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config
        self.api_client: Optional[OneCApiClient] = None
        
        # Создаем MCP сервер  
        self.server = Server("onec-ai-1c-enterprise")
        
        # Регистрируем обработчики
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрация обработчиков MCP."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """Список доступных инструментов."""
            return [
                Tool(
                    name="ask_1c_ai",
                    description="🔍 Задать любой вопрос специализированному ИИ-ассистенту 1С.ai (1С:Напарник) по платформе 1С:Предприятие. Используется для вопросов о 1С, конфигурации, объектах платформы, встроенном языке, API, интеграции и разработке.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Вопрос для модели 1С.ai"
                            },
                            "programming_language": {
                                "type": "string",
                                "description": "Язык программирования (опционально)",
                                "default": ""
                            },
                            "create_new_session": {
                                "type": "boolean",
                                "description": "Создать новую сессию для этого вопроса",
                                "default": False
                            }
                        },
                        "required": ["question"]
                    },
                ),
                Tool(
                    name="explain_1c_syntax",
                    description="📚 Объяснить синтаксис, конструкции и объекты языка 1С:Предприятие. Используется для объяснения HTTPСоединение, HTTPЗапрос, ТаблицаЗначений, Запрос, РегистрСведений, Документ, Справочник, Для Каждого, Если, Процедура, Функция и других элементов 1С.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "syntax_element": {
                                "type": "string",
                                "description": "Элемент синтаксиса или объект 1С для объяснения (например: HTTPСоединение, HTTPЗапрос, ТаблицаЗначений, РегистрСведений, Документ, Справочник, Запрос, Для Каждого, Если, Процедура, Функция)"
                            },
                            "context": {
                                "type": "string",
                                "description": "Дополнительный контекст использования (опционально)",
                                "default": ""
                            }
                        },
                        "required": ["syntax_element"]
                    },
                ),
                Tool(
                    name="check_1c_code",
                    description="🔧 Проверить и проанализировать код 1С:Предприятие на ошибки, производительность и соответствие лучшим практикам. Используется для валидации кода на встроенном языке 1С.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Код 1С для проверки и анализа"
                            },
                            "check_type": {
                                "type": "string",
                                "description": "Тип проверки: syntax (синтаксис), logic (логика), performance (производительность)",
                                "enum": ["syntax", "logic", "performance"],
                                "default": "syntax"
                            }
                        },
                        "required": ["code"]
                    },
                ),

            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """Обработка вызова инструментов."""
            
            # Отладочное логирование (без эмодзи для избежания проблем с кодировкой)
            # print(f"MCP tool call: {name} with args: {arguments}", flush=True)
            
            # Инициализируем конфигурацию и API клиент если нужно
            if self.config is None:
                try:
                    self.config = get_config()
                except Exception as e:
                    return [types.TextContent(
                        type="text",
                        text=f"Ошибка конфигурации: {str(e)}\nУстановите переменную окружения ONEC_AI_TOKEN"
                    )]
            
            if self.api_client is None:
                try:
                    self.api_client = OneCApiClient(self.config)
                except Exception as e:
                    return [types.TextContent(
                        type="text",
                        text=f"Ошибка подключения к API: {str(e)}"
                    )]
            
            try:
                if name == "ask_1c_ai":
                    return await self._handle_ask_1c_ai(arguments)
                elif name == "explain_1c_syntax":
                    return await self._handle_explain_syntax(arguments)
                elif name == "check_1c_code":
                    return await self._handle_check_code(arguments)
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"Неизвестный инструмент: {name}"
                    )]
                    
            except ApiError as e:
                logger.error(f"Ошибка API при вызове {name}: {e.message}")
                return [types.TextContent(
                    type="text",
                    text=f"Ошибка при обращении к 1С.ai: {e.message}"
                )]
            except Exception as e:
                logger.error(f"Неожиданная ошибка при вызове {name}: {str(e)}")
                return [types.TextContent(
                    type="text",
                    text=f"Произошла неожиданная ошибка: {str(e)}"
                )]
    
    async def _handle_ask_1c_ai(self, arguments: dict) -> list[types.TextContent]:
        """Обработка инструмента ask_1c_ai."""
        question = arguments.get("question", "")
        programming_language = arguments.get("programming_language", "")
        create_new_session = arguments.get("create_new_session", False)
        
        if not question.strip():
            return [types.TextContent(
                type="text",
                text="Ошибка: Вопрос не может быть пустым"
            )]
        
        # Получаем или создаем сессию
        conversation_id = await self.api_client.get_or_create_session(
            create_new=create_new_session,
            programming_language=programming_language or None
        )
        
        # Отправляем вопрос
        answer = await self.api_client.send_message(conversation_id, question)
        
        # Очищаем ответ от проблемных символов
        clean_answer = self._sanitize_text(answer)
        
        return [types.TextContent(
            type="text",
            text=f"Ответ от 1С.ai:\n\n{clean_answer}\n\nСессия: {conversation_id}"
        )]
    
    async def _handle_explain_syntax(self, arguments: dict) -> list[types.TextContent]:
        """Обработка инструмента explain_1c_syntax."""
        syntax_element = arguments.get("syntax_element", "")
        context = arguments.get("context", "")
        
        if not syntax_element.strip():
            return [types.TextContent(
                type="text",
                text="Ошибка: Элемент синтаксиса не может быть пустым"
            )]
        
        # Формируем вопрос для модели
        question = f"Объясни синтаксис и использование: {syntax_element}"
        if context:
            question += f" в контексте: {context}"
        
        # Получаем сессию и отправляем вопрос
        conversation_id = await self.api_client.get_or_create_session()
        answer = await self.api_client.send_message(conversation_id, question)
        
        # Очищаем ответ от проблемных символов
        clean_answer = self._sanitize_text(answer)
        
        return [types.TextContent(
            type="text",
            text=f"Объяснение синтаксиса '{syntax_element}':\n\n{clean_answer}"
        )]
    
    async def _handle_check_code(self, arguments: dict) -> list[types.TextContent]:
        """Обработка инструмента check_1c_code."""
        code = arguments.get("code", "")
        check_type = arguments.get("check_type", "syntax")
        
        if not code.strip():
            return [types.TextContent(
                type="text",
                text="Ошибка: Код для проверки не может быть пустым"
            )]
        
        # Формируем вопрос в зависимости от типа проверки
        check_descriptions = {
            "syntax": "синтаксические ошибки",
            "logic": "логические ошибки и потенциальные проблемы",
            "performance": "проблемы производительности и оптимизации"
        }
        
        check_desc = check_descriptions.get(check_type, "ошибки")
        question = f"Проверь этот код 1С на {check_desc} и дай рекомендации:\n\n```1c\n{code}\n```"
        
        # Получаем сессию и отправляем вопрос
        conversation_id = await self.api_client.get_or_create_session()
        answer = await self.api_client.send_message(conversation_id, question)
        
        # Очищаем ответ от проблемных символов
        clean_answer = self._sanitize_text(answer)
        
        return [types.TextContent(
            type="text",
            text=f"Проверка кода на {check_desc}:\n\n{clean_answer}"
        )]
    

    
    async def run(self, transport: str = "stdio"):
        """Запуск MCP сервера."""
        try:
            # Не проверяем конфигурацию при запуске - будем делать это при первом вызове инструмента
            
            # Запускаем сервер
            if transport == "stdio":
                from mcp.server.stdio import stdio_server
                async with stdio_server() as (read_stream, write_stream):
                    await self.server.run(
                        read_stream,
                        write_stream,
                        InitializationOptions(
                            server_name="MCP_1copilot",
                            server_version="0.1.0",
                            capabilities=self.server.get_capabilities(
                                notification_options=NotificationOptions(),
                                experimental_capabilities={},
                            ),
                        ),
                    )
            else:
                raise ValueError(f"Неподдерживаемый транспорт: {transport}")
                
        except Exception as e:
            logger.error(f"Ошибка при запуске сервера: {str(e)}")
            raise
        finally:
            # Закрываем API клиент
            if self.api_client:
                await self.api_client.close()


async def main():
    """Главная функция запуска сервера."""
    try:
        server = OneCMcpServer()
        await server.run()
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 