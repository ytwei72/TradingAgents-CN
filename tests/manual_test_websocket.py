"""
WebSocket 功能手动测试脚本
"""
import asyncio
import websockets
import json
import time
import threading
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.getcwd())

async def test_websocket_client():
    uri = "ws://localhost:8000/ws/notifications"
    print(f"正在连接到 {uri} ...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 连接成功!")
            
            # 发送 Ping
            print("发送: ping")
            await websocket.send("ping")
            response = await websocket.recv()
            print(f"接收: {response}")
            
            if response == "pong":
                print("✅ Ping/Pong 测试通过")
            else:
                print("❌ Ping/Pong 测试失败")
            
            print("正在等待通知推送 (请在另一个终端触发分析任务)...")
            print("按 Ctrl+C 退出")
            
            while True:
                message = await websocket.recv()
                print(f"📩 收到通知: {message}")
                
    except ConnectionRefusedError:
        print("❌ 连接失败: 无法连接到服务器，请确保服务器已启动 (uv run uvicorn app.main:app ...)")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_websocket_client())
    except KeyboardInterrupt:
        print("\n测试结束")
