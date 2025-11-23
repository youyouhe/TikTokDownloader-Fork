#!/usr/bin/env python3
"""
直接启动API服务器的脚本（带详细调试日志）
"""
import asyncio
import logging
import sys
from datetime import datetime
from src.application import TikTokDownloader


def setup_logging():
    """设置详细的日志记录"""
    # 设置根日志级别
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'api_server_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )

    # 设置关键库的日志级别
    logging.getLogger("httpx").setLevel(logging.DEBUG)  # HTTP请求日志
    logging.getLogger("uvicorn").setLevel(logging.DEBUG)  # Uvicorn服务器日志
    logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)  # Uvicorn访问日志
    logging.getLogger("fastapi").setLevel(logging.DEBUG)  # FastAPI框架日志
    logging.getLogger("src").setLevel(logging.DEBUG)  # 应用程序日志


async def main():
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("正在启动TikTokDownloader API服务器...")

    async with TikTokDownloader() as downloader:
        try:
            logger.info("初始化配置和设置...")
            # 直接初始化设置
            downloader.check_config()
            await downloader.check_settings(False)

            # 启动API服务器
            print("=" * 60)
            print("🚀 TikTokDownloader API 服务器启动中...")
            print("=" * 60)
            print("📖 API文档: http://127.0.0.1:5555/docs")
            print("📖 ReDoc文档: http://127.0.0.1:5555/redoc")
            print("🔗 项目主页: http://127.0.0.1:5555")
            print("=" * 60)
            print("⏹️  按 Ctrl+C 停止服务器")
            print("=" * 60)

            from src.application.main_server import APIServer
            from src.custom import SERVER_HOST, SERVER_PORT
            import uvicorn

            logger.info(f"服务器地址: {SERVER_HOST}:{SERVER_PORT}")
            logger.info("正在启动API服务器...")

            # 使用内置方法启动服务器
            await APIServer(
                downloader.parameter,
                downloader.database,
            ).run_server(SERVER_HOST, SERVER_PORT, log_level="debug")

        except KeyboardInterrupt:
            logger.info("收到停止信号，正在关闭服务器...")
        except Exception as e:
            logger.error(f"启动服务器时发生错误: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())