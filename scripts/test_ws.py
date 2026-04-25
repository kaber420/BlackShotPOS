import urllib.request
import asyncio
import websockets

async def test():
    uri = "ws://127.0.0.1:8400/api/v1/pos/ws/iot?token=test-token-123"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            msg = await websocket.recv()
            print("Received:", msg)
    except Exception as e:
        print("Error:", e)
if __name__ == '__main__':
    asyncio.run(test())
