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


def main():
    server_address: str = input("server address: ")
    while True:
        user_input: str = input("server port: ")
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

    length_data: bytes = tcp_client.recv(PREFIX_LENGTH)
    (response_data_length,) = struct.unpack("!I", length_data)
    response_data: bytes = tcp_client.recv(response_data_length)
    response_data_json: dict[str, int] = json.loads(response_data.decode())
    print(response_data_json)

    # video_file_path: str = (
    #     "/home/haru/project/Recursion/VideoCompressorService/test/input/sample.mp4"
    # )
    # with open(video_file_path, "rb") as video_file:
    #     while True:
    #         bytes_read = video_file.read(BUFFER_SIZE)
    #         if not bytes_read:
    #             break
    #         tcp_client.sendall(bytes_read)

    tcp_client.close()


if __name__ == "__main__":
    main()
