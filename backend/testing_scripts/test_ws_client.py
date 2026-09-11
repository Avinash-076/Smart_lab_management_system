import asyncio
import websockets

COMPUTER_ID = 1
CREDENTIAL = "f1175fb30ed94976090745230054f558eb764660221250f6e0532408c34a1e5c"

async def main():
    print("Connecting to the server as a computer...")
    uri = f"ws://127.0.0.1:8000/ws/client/{COMPUTER_ID}?credential={CREDENTIAL}"
    websocket = await websockets.connect(uri)
    print("Connected! Computer marked online.")
    print("Sending 2 pings, then going silent WITHOUT closing (simulates a frozen/crashed agent).")

    await asyncio.sleep(5)
    await websocket.send("ping")
    print("Sent ping 1")

    await asyncio.sleep(5)
    await websocket.send("ping")
    print("Sent ping 2")

    print("Now going silent. The connection object stays open, but nothing more is sent.")
    print("Watch the server terminal and check the database — the safety net should force-close this after ~15s (shortened for testing).")
    await asyncio.sleep(60)  # just keep the process alive, sending nothing

asyncio.run(main())