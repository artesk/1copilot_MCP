"""Конфигурация для MCP сервера 1С.ai."""

import os
from typing import Optional
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


class Config(BaseSettings):
    """Конфигурация приложения."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    # API настройки
    onec_ai_token: str = Field(
        ..., 
        validation_alias=AliasChoices('ONEC_AI_TOKEN', 'onec_ai_token'),
        description="Токен для доступа к API 1С.ai"
    )
    base_url: str = Field(
        default="https://code.1c.ai", 
        env="ONEC_AI_BASE_URL", 
        description="Базовый URL API"
    )
    timeout: int = Field(
        default=30, 
        env="ONEC_AI_TIMEOUT", 
        description="Таймаут для запросов в секундах"
    )
    
    # Настройки модели
    ui_language: str = Field(
        default="russian", 
        env="ONEC_AI_UI_LANGUAGE", 
        description="Язык интерфейса"
    )
    programming_language: str = Field(
        default="", 
        env="ONEC_AI_PROGRAMMING_LANGUAGE", 
        description="Язык программирования по умолчанию"
    )
    script_language: str = Field(
        default="", 
        env="ONEC_AI_SCRIPT_LANGUAGE", 
        description="Скриптовый язык по умолчанию"
    )
    
    # Настройки сессий
    max_active_sessions: int = Field(
        default=10, 
        env="MAX_ACTIVE_SESSIONS", 
        description="Максимальное количество активных сессий"
    )
    session_ttl: int = Field(
        default=3600, 
        env="SESSION_TTL", 
        description="Время жизни сессии в секундах"
    )
    



def get_config() -> Config:
    """Получить конфигурацию приложения."""
    return Config() 