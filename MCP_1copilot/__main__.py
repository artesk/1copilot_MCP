"""Точка входа для запуска MCP сервера 1С.ai."""

import asyncio
import sys
from .mcp_server import main

def cli_main():
    """Консольная точка входа."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nЗавершение работы сервера...")
        sys.exit(0)
    except Exception as e:
        print(f"Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    cli_main() 