from typing import Any
import asyncio
import socket
import json
import os


BUFFER_SIZE: int = 1024


async def handle_client(client, loop) -> None:
    video_path: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "tmp/before_process/output_video.mp4",
    )
    with open(video_path, "wb") as video_file:
        while data := await loop.sock_recv(client, BUFFER_SIZE):
            if not data:
                break
            video_file.write(data)
    client.close()


async def run_tcp_server() -> None:
    config_file_path: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config/config.json"
    )
    with open(config_file_path, "r") as f:
        config: dict[str, Any] = json.load(f)
    TCP_SERVER_ADDRESS: str = config["address"]
    TCP_SERVER_PORT: int = config["port"]
    CLIENT_CONN_TIME_OUT: int = config["client_connection_time_out"]

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setblocking(False)
    server.bind((TCP_SERVER_ADDRESS, TCP_SERVER_PORT))
    server.listen()
    loop = asyncio.get_event_loop()

    while True:
        client, address = await loop.sock_accept(server)
        client.settimeout(CLIENT_CONN_TIME_OUT)
        print(f"Connection from {address}")
        asyncio.create_task(handle_client(client, loop))


if __name__ == "__main__":
    asyncio.run(run_tcp_server())
