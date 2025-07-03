#!/usr/bin/env python3
"""Простой тест MCP сервера 1С.ai."""

import asyncio
from MCP_1copilot.config import get_config
from MCP_1copilot.api_client import OneCApiClient


async def test_api_client():
    """Тест API клиента."""
    print("🔧 Тестирование API клиента 1С.ai...")
    
    try:
        # Проверяем наличие токена
        config = get_config()
        if not config.onec_ai_token:
            print("❌ Не найден токен ONEC_AI_TOKEN в переменных окружения")
            print("   Установите токен: export ONEC_AI_TOKEN='ваш_токен'")
            return False
        
        print(f"✅ Конфигурация загружена:")
        print(f"   - Базовый URL: {config.base_url}")
        print(f"   - Язык интерфейса: {config.ui_language}")
        print(f"   - Таймаут: {config.timeout}s")
        
        # Создаем API клиент
        async with OneCApiClient(config) as client:
            print("\n🚀 Тестирование создания дискуссии...")
            
            # Создаем дискуссию
            conversation_id = await client.create_conversation()
            print(f"✅ Дискуссия создана: {conversation_id}")
            
            # Отправляем тестовый вопрос
            print("\n💬 Отправка тестового вопроса...")
            test_question = "Что такое HTTPСоединение в 1С?"
            answer = await client.send_message(conversation_id, test_question)
            
            print(f"❓ Вопрос: {test_question}")
            print(f"✅ Ответ получен ({len(answer)} символов):")
            print("-" * 50)
            print(answer[:200] + "..." if len(answer) > 200 else answer)
            print("-" * 50)
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {str(e)}")
        return False


def test_config():
    """Тест конфигурации."""
    print("🔧 Тестирование конфигурации...")
    
    try:
        config = get_config()
        print("✅ Конфигурация успешно загружена")
        return True
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {str(e)}")
        return False


async def main():
    """Главная функция тестирования."""
    print("🧪 Запуск тестов MCP сервера 1С.ai\n")
    
    # Тест конфигурации
    if not test_config():
        return
    
    print()
    
    # Тест API клиента
    if not await test_api_client():
        return
    
    print("\n🎉 Все тесты прошли успешно!")
    print("\n📋 Для запуска MCP сервера используйте:")
    print("   python -m MCP_1copilot")


if __name__ == "__main__":
    asyncio.run(main()) 