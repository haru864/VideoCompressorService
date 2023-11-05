import os
import struct
from typing import Any
import socket
import json

BUFFER_SIZE: int = 1024
PREFIX_LENGTH: int = 4
operation_list: list[str] = [
    "compress",
    "change_resolution",
    "change_aspect_ratio",
    "convert_to_audio",
    "trim_by_time_range",
]
compress_level_to_bitrate_multiplier: dict[str, int] = {
    "low": 0.9,
    "medium": 0.7,
    "high": 0.5,
}


def receive_status(sock: socket.socket) -> dict[str, Any]:
    length_data: bytes = sock.recv(PREFIX_LENGTH)
    (response_data_length,) = struct.unpack("!I", length_data)
    response_data: bytes = sock.recv(response_data_length)
    response_data_json: dict[str, int] = json.loads(response_data.decode())
    return response_data_json


def recvall(sock, length) -> bytes:
    # print(f"length -> {length}")
    data = b""
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise Exception("接続が中断されました。")
        data += more
    return data


def main() -> None:
    # server_address: str = input("server address: ")
    server_address: str = "127.0.0.1"
    while True:
        # user_input: str = input("server port: ")
        user_input: str = "9001"
        try:
            server_port: int = int(user_input)
            break
        except Exception:
            print("数値を入力してください")
    print(f"Connecting to ({server_address}, {server_port})")
    tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_client.connect((server_address, server_port))

    request_data: dict[str, Any] = {}
    print("Choose the operation number.")
    for index, operation in enumerate(operation_list):
        print(f" {index+1}.{operation}")
    while True:
        try:
            user_input: str = int(input("operation number: "))
            if user_input < 1 or user_input > len(operation_list):
                print(f"1~{len(operation_list)} is available")
                continue
            request_data["operation"] = operation_list[user_input - 1]
            break
        except Exception:
            print("Please enter operation number")

    if request_data["operation"] == "compress":
        print("Choose compress level.")
        for index, compress_level in enumerate(
            compress_level_to_bitrate_multiplier.keys()
        ):
            print(f" {index+1}.{compress_level}")
        while True:
            try:
                user_input: str = int(input("compress level: "))
                if user_input < 1 or user_input > len(
                    compress_level_to_bitrate_multiplier
                ):
                    print(f"1~{len(compress_level_to_bitrate_multiplier)} is available")
                    continue
                request_data["compress_level"] = list(
                    compress_level_to_bitrate_multiplier.values()
                )[user_input - 1]
                break
            except Exception:
                print("Please enter compress level")

    json_str: str = json.dumps(request_data)
    data: bytes = json_str.encode()
    data_length_prefix: bytes = struct.pack("!I", len(data))
    tcp_client.sendall(data_length_prefix + data)

    response_data_json: dict[str, int] = receive_status(tcp_client)
    print(f"operation check result -> {response_data_json}")
    if response_data_json["status"] == 1:
        print(response_data_json.get("error"))
        tcp_client.close()
        return None

    # TODO ファイルパスはユーザーが入力できるようにする
    # video_file_path: str = input("video file path: ")
    # output_dir_path: str = input("output path: ")
    video_file_path: str = (
        "/home/haru/project/Recursion/VideoCompressorService/test/input/sample.mp4"
    )
    output_file_path: str = (
        "/home/haru/project/Recursion/VideoCompressorService/test/output/sample.mp4"
    )
    video_file_name: str = os.path.basename(video_file_path)
    video_file_name_data: bytes = video_file_name.encode()
    data_length_prefix: bytes = struct.pack("!I", len(video_file_name_data))
    tcp_client.sendall(data_length_prefix + video_file_name_data)

    with open(video_file_path, "rb") as video_file:
        while bytes_read := video_file.read(BUFFER_SIZE):
            length = len(bytes_read)
            tcp_client.sendall(struct.pack("!I", length))
            tcp_client.sendall(bytes_read)
    data_length_prefix: bytes = struct.pack("!I", 0)
    tcp_client.sendall(data_length_prefix)

    response_data_json: dict[str, int] = receive_status(tcp_client)
    print(f"processing video result -> {response_data_json}")
    if response_data_json["status"] == 1:
        print(response_data_json.get("error"))
        tcp_client.close()
        return None

    with open(output_file_path, "wb") as video_file:
        while True:
            raw_length = recvall(tcp_client, PREFIX_LENGTH)
            length = struct.unpack("!I", raw_length)[0]
            if length == 0:
                break
            data = recvall(tcp_client, length)
            video_file.write(data)

    tcp_client.close()


if __name__ == "__main__":
    main()
