import struct
from typing import Any
import socket
import json
import os
import ffmpeg

BUFFER_SIZE: int = 1024
PREFIX_LENGTH: int = 4


def recvall(sock, length) -> bytes:
    # print(f"length -> {length}")
    data = b""
    while len(data) < length:
        more = sock.recv(length - len(data))
        print(f"received {len(more)} bytes")
        if not more:
            raise Exception("接続が中断されました。")
        data += more
    return data


def send_status(sock, error_msg: str | None = None):
    if error_msg is None:
        response_str: str = json.dumps({"status": 0})
    else:
        response_str: str = json.dumps({"status": 1, "error": error_msg})
    data: bytes = response_str.encode()
    data_length_prefix: bytes = struct.pack("!I", len(data))
    sock.sendall(data_length_prefix + data)


def handle_client(client_socket: socket.socket) -> None:
    length_data = client_socket.recv(PREFIX_LENGTH)
    (length,) = struct.unpack("!I", length_data)
    data = client_socket.recv(length)
    json_data = json.loads(data.decode())
    print(json_data)

    try:
        requested_operation: str = json_data["operation"]
        if requested_operation == "compress":
            compress_level: float = json_data["compress_level"]
            if compress_level not in (0.5, 0.7, 0.9):
                raise Exception("Invalid compress level")
        else:
            raise Exception("Invalid operation")
        send_status(client_socket)
    except Exception as e:
        print(e)
        send_status(client_socket, str(e))
        client_socket.close()

    length_data = client_socket.recv(PREFIX_LENGTH)
    (length,) = struct.unpack("!I", length_data)
    video_file_name_data: bytes = client_socket.recv(length)
    video_file_name: str = video_file_name_data.decode()
    video_path_bef_proc: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        f"tmp/before_process/{video_file_name}",
    )
    video_path_aft_proc: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        f"tmp/after_process/{video_file_name}",
    )

    with open(video_path_bef_proc, "wb") as video_file:
        while True:
            raw_length = recvall(client_socket, PREFIX_LENGTH)
            length = struct.unpack("!I", raw_length)[0]
            if length == 0:
                break
            data = recvall(client_socket, length)
            video_file.write(data)

    try:
        probe: dict[Any, Any] = ffmpeg.probe(video_path_bef_proc)
        print(probe)
        video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")
        default_bitrate_str: str = video_info["bit_rate"]
        default_bitrate: int = int(default_bitrate_str)
        compressed_bitrate: int = int(default_bitrate * compress_level)
        print(f"default_bitrate -> {default_bitrate}")
        print(f"compressed_bitrate -> {compressed_bitrate}")
        stream = ffmpeg.input(video_path_bef_proc).output(
            video_path_aft_proc, video_bitrate=compressed_bitrate
        )
        ffmpeg.run(stream, overwrite_output=True)
        send_status(client_socket)
    except Exception as e:
        print(e)
        send_status(client_socket, str(e))

    with open(video_path_aft_proc, "rb") as video_file:
        while bytes_read := video_file.read(BUFFER_SIZE):
            length = len(bytes_read)
            client_socket.sendall(struct.pack("!I", length))
            client_socket.sendall(bytes_read)
    data_length_prefix: bytes = struct.pack("!I", 0)
    client_socket.sendall(data_length_prefix)

    client_socket.close()


def run_tcp_server() -> None:
    config_file_path: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config/config.json"
    )
    with open(config_file_path, "r") as f:
        config: dict[str, Any] = json.load(f)
    TCP_SERVER_ADDRESS: str = config["address"]
    TCP_SERVER_PORT: int = config["port"]
    CLIENT_CONN_TIME_OUT: int = config["client_connection_time_out"]

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((TCP_SERVER_ADDRESS, TCP_SERVER_PORT))
        server_socket.listen()
        print(f"Server is listening on {TCP_SERVER_ADDRESS}:{TCP_SERVER_PORT}")
        client_socket, addr = server_socket.accept()
        client_socket.settimeout(CLIENT_CONN_TIME_OUT)
        print(f"Connection from {addr}")
        handle_client(client_socket)


if __name__ == "__main__":
    run_tcp_server()
