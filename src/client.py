import os
import struct
from typing import Any
import socket
import json
import ffmpeg
import re

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


def is_mp4_file(file_path):
    return os.path.isfile(file_path) and file_path.lower().endswith(".mp4")


def is_valid_directory(dir_path):
    return os.path.isdir(dir_path) and dir_path.endswith("/")


def receive_status(sock: socket.socket) -> dict[str, Any]:
    length_data: bytes = sock.recv(PREFIX_LENGTH)
    (response_data_length,) = struct.unpack("!I", length_data)
    response_data: bytes = sock.recv(response_data_length)
    response_data_json: dict[str, int] = json.loads(response_data.decode())
    return response_data_json


def recvall(sock: socket.socket, length: int) -> bytes:
    data = b""
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise Exception("Connection interrupted")
        data += more
    return data


def displayResolution(video_file_path: str):
    probe: dict[Any, Any] = ffmpeg.probe(video_file_path)
    video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")
    width: int = video_info["width"]
    height: int = video_info["height"]
    print("Video Resolution")
    print(f" width: {width}")
    print(f" height: {height}")


def displayAspectRatio(video_file_path: str):
    probe: dict[Any, Any] = ffmpeg.probe(video_file_path)
    video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")
    display_aspect_ratio: str = video_info["display_aspect_ratio"]
    print(f"Display Aspect Ratio {display_aspect_ratio}")


def main() -> None:
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

    while video_file_path := input("video file path: "):
        if is_mp4_file(video_file_path):
            break
        print("Set the path to any MP4 files that exist")
    while output_dir_path := input("output path: "):
        if is_valid_directory(output_dir_path):
            break
        print("Set the path of the existing directory with the '/' end")
    video_file_name_with_extension: str = os.path.basename(video_file_path)
    video_file_name, video_file_extension = os.path.splitext(
        video_file_name_with_extension
    )

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
                request_data["compress_leverage"] = list(
                    compress_level_to_bitrate_multiplier.values()
                )[user_input - 1]
                break
            except Exception:
                print("Please enter compress level")
    elif request_data["operation"] == "change_resolution":
        displayResolution(video_file_path)
        while True:
            try:
                new_width: int = int(input("new width: "))
                new_height: int = int(input("new height: "))
                if new_width <= 0 or new_height <= 0:
                    raise Exception("Width or height must be positive number")
                break
            except Exception as e:
                print(e)
        request_data["width"] = new_width
        request_data["height"] = new_height
    elif request_data["operation"] == "change_aspect_ratio":
        displayAspectRatio(video_file_path)
        while new_aspect_ratio := input("new aspect ratio (w/h): "):
            aspect_ratio_pattern = r"^\d+/\d+$"
            if re.match(aspect_ratio_pattern, new_aspect_ratio):
                break
            print("Aspect ratio is a 'positive integer/positive integer' format")
        request_data["aspect_ratio"] = new_aspect_ratio
    elif request_data["operation"] == "convert_to_audio":
        pass
    elif request_data["operation"] == "trim_by_time_range":
        while True:
            try:
                start_seconds: int = int(input("start_seconds: "))
                end_seconds: int = int(input("end_seconds: "))
                if start_seconds < 0 or end_seconds < 0:
                    raise Exception(
                        "'start_seconds' and 'end_seconds' must be equal or greater than zero"
                    )
                if start_seconds > end_seconds:
                    raise Exception(
                        "'end_seconds' must be equal or greater than 'start_seconds'"
                    )
                break
            except Exception as e:
                print(e)
        request_data["start_seconds"] = start_seconds
        request_data["end_seconds"] = end_seconds
    else:
        print("unimplemented operation")
        tcp_client.close()
        return

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

    video_file_name_data: bytes = video_file_name_with_extension.encode()
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

    if request_data["operation"] == "convert_to_audio":
        output_file_path: str = f"{output_dir_path}{video_file_name}.mp3"
    elif request_data["operation"] == "trim_by_time_range":
        output_file_path: str = f"{output_dir_path}{video_file_name}.webm"
    else:
        output_file_path: str = (
            f"{output_dir_path}{video_file_name}{video_file_extension}"
        )

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
