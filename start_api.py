#!/usr/bin/env python3
"""
直接启动API服务器的脚本
"""
import asyncio
from src.application import TikTokDownloader


async def main():
    async with TikTokDownloader() as downloader:
        # 直接初始化设置
        downloader.check_config()
        await downloader.check_settings(False)

        # 启动API服务器
        print("正在启动API服务器...")
        print("访问 http://127.0.0.1:5555/docs 查看API文档")
        print("访问 http://127.0.0.1:5555/redoc 查看API文档")
        print("按 Ctrl+C 停止服务器")

        from src.application.main_server import APIServer
        from src.custom import SERVER_HOST, SERVER_PORT

        await APIServer(
            downloader.parameter,
            downloader.database,
        ).run_server(SERVER_HOST, SERVER_PORT)


if __name__ == "__main__":
    asyncio.run(main())