#!/usr/bin/env python3
"""
监控API请求的简单工具
"""
import logging
import sys
from datetime import datetime

def setup_api_monitoring():
    """设置API监控日志"""
    # 创建logger
    logger = logging.getLogger('API_MONITOR')
    logger.setLevel(logging.DEBUG)

    # 创建handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    # 创建formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)

    # 添加handler到logger
    logger.addHandler(handler)

    # 设置其他库的日志级别
    logging.getLogger("httpx").setLevel(logging.DEBUG)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

if __name__ == "__main__":
    setup_api_monitoring()
    logging.info("API监控已启动，现在请运行API服务器...")

    # 保持程序运行
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("停止监控")