import asyncio
import websockets

ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzg5MTIxODQzLCJ0eXBlIjoiYWNjZXNzIn0.y8WCsA2w053tNrvXS7fc2VOeWUsvbDTva2aHR7dAeMc"  # ← replace with your value from Step 0C

async def main():
    uri = f"ws://127.0.0.1:8000/ws/dashboard?token={ACCESS_TOKEN}"
    async with websockets.connect(uri) as websocket:
        print("Dashboard connected. Waiting for status updates...")
        async for message in websocket:
            print("Received update:", message)

asyncio.run(main()) 