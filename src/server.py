import struct
from typing import Any
import socket
import json
import os
import ffmpeg

BUFFER_SIZE: int = 1024
PREFIX_LENGTH: int = 4


def recvall(sock, length) -> bytes:
    data = b""
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise Exception("Connection interrupted")
        data += more
    return data


def send_status(sock, error_msg: str | None = None) -> None:
    if error_msg is None:
        response_str: str = json.dumps({"status": 0})
    else:
        response_str: str = json.dumps({"status": 1, "error": error_msg})
    data: bytes = response_str.encode()
    data_length_prefix: bytes = struct.pack("!I", len(data))
    sock.sendall(data_length_prefix + data)


def compress_video(
    input_video_file: str, output_video_file: str, compress_leverage: float
) -> None:
    probe: dict[Any, Any] = ffmpeg.probe(input_video_file)
    video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")
    default_bitrate: int = int(video_info["bit_rate"])
    compressed_bitrate: int = int(default_bitrate * compress_leverage)
    stream = ffmpeg.input(input_video_file).output(
        output_video_file, video_bitrate=compressed_bitrate
    )
    ffmpeg.run(stream, overwrite_output=True)


def change_video_resolution(
    input_video: str, output_video: str, new_width: int, new_height: int
):
    input_stream = ffmpeg.input(input_video)
    video = input_stream.filter("scale", new_width, new_height)
    audio = input_stream.audio
    out = ffmpeg.output(video, audio, output_video)
    out.run(overwrite_output=True)


def change_video_aspect_ratio(
    input_video: str, output_video: str, new_aspect_ratio: str
):
    input_stream = ffmpeg.input(input_video)
    video = input_stream.filter("setdar", new_aspect_ratio)
    audio = input_stream.audio
    out = ffmpeg.output(video, audio, output_video)
    out.run(overwrite_output=True)


def convert_to_audio(input_video: str, output_audio: str):
    stream = ffmpeg.input(input_video).output(output_audio, format="mp3")
    ffmpeg.run(stream, overwrite_output=True)


def handle_client(client_socket: socket.socket) -> None:
    length_data = client_socket.recv(PREFIX_LENGTH)
    (length,) = struct.unpack("!I", length_data)
    data = client_socket.recv(length)
    json_data = json.loads(data.decode())

    try:
        requested_operation: str = json_data["operation"]
        if requested_operation == "compress":
            compress_leverage: float = json_data["compress_leverage"]
        elif requested_operation == "change_resolution":
            new_width: float = json_data["width"]
            new_height: float = json_data["height"]
        elif requested_operation == "change_aspect_ratio":
            new_aspect_ratio: str = json_data["aspect_ratio"]
        send_status(client_socket)
    except Exception as e:
        print(e)
        send_status(client_socket, str(e))
        client_socket.close()

    length_data = client_socket.recv(PREFIX_LENGTH)
    (length,) = struct.unpack("!I", length_data)
    video_file_name_data: bytes = client_socket.recv(length)
    video_file_name, video_file_extension = os.path.splitext(
        video_file_name_data.decode()
    )
    video_path_bef_proc: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        f"tmp/before_process/{video_file_name}{video_file_extension}",
    )

    with open(video_path_bef_proc, "wb") as video_file:
        while True:
            raw_length = recvall(client_socket, PREFIX_LENGTH)
            length = struct.unpack("!I", raw_length)[0]
            if length == 0:
                break
            data = recvall(client_socket, length)
            video_file.write(data)

    output_path_aft_proc: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        f"tmp/after_process/{video_file_name}",
    )
    if requested_operation == "convert_to_audio":
        output_path_aft_proc += ".mp3"
    elif requested_operation == "trim_by_time_range":
        output_path_aft_proc += ".gif"
    else:
        output_path_aft_proc += ".mp4"

    try:
        if requested_operation == "compress":
            compress_video(video_path_bef_proc, output_path_aft_proc, compress_leverage)
        elif requested_operation == "change_resolution":
            change_video_resolution(
                video_path_bef_proc, output_path_aft_proc, new_width, new_height
            )
        elif requested_operation == "change_aspect_ratio":
            change_video_aspect_ratio(
                video_path_bef_proc, output_path_aft_proc, new_aspect_ratio
            )
        elif requested_operation == "convert_to_audio":
            convert_to_audio(video_path_bef_proc, output_path_aft_proc)
        send_status(client_socket)
    except Exception as e:
        print(e)
        send_status(client_socket, str(e))

    with open(output_path_aft_proc, "rb") as video_file:
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
