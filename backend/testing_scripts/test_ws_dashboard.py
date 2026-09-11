import asyncio
import websockets

ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzg3NDE3ODg0LCJ0eXBlIjoiYWNjZXNzIn0.RHfONbfexIG5lPJ16X6gFl_Q83XjnvktiQM10jzH-7U"  # ← replace with your value from Step 0C

async def main():
    uri = f"ws://127.0.0.1:8000/ws/dashboard?token={ACCESS_TOKEN}"
    async with websockets.connect(uri) as websocket:
        print("Dashboard connected. Waiting for status updates...")
        async for message in websocket:
            print("Received update:", message)

asyncio.run(main()) 