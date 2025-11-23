#!/usr/bin/env python3
"""
测试API中间件的独立脚本
"""
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

# 创建测试FastAPI应用
app = FastAPI(title="Test API")

# 添加请求日志中间件（和主项目相同）
@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start_time = time.time()

    # 记录请求开始
    print(f"\n🔥 [{time.strftime('%Y-%m-%d %H:%M:%S')}] {request.method} {request.url}")
    print(f"📍 Client: {request.client.host if request.client else 'unknown'}")
    print(f"🌐 User-Agent: {request.headers.get('user-agent', 'unknown')}")

    # 对于POST请求，尝试记录请求体
    if request.method == "POST":
        try:
            body = await request.body()
            if body:
                content = body.decode('utf-8')
                # 只记录前200个字符，避免太长
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"📤 Request Body: {preview}")
        except Exception as e:
            print(f"⚠️ Could not read request body: {e}")

    # 处理请求
    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # 记录响应
        print(f"✅ Status: {response.status_code}")
        print(f"⏱️ Time: {process_time:.3f}s")
        print("-" * 80)

        return response
    except Exception as e:
        process_time = time.time() - start_time
        print(f"❌ Error: {e}")
        print(f"⏱️ Failed after: {process_time:.3f}s")
        print("-" * 80)
        raise

# 测试路由
@app.get("/")
async def root():
    return {"message": "Test API is working"}

@app.post("/test")
async def test_endpoint():
    return {"message": "Test POST endpoint", "status": "success"}

if __name__ == "__main__":
    print("🚀 启动测试API服务器...")
    print("📍 地址: http://127.0.0.1:8000")
    print("📖 文档: http://127.0.0.1:8000/docs")
    print("⏹️ 按 Ctrl+C 停止服务器")
    print("=" * 60)

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="debug",
        access_log=True
    )