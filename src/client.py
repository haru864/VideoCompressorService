import socket
import os


BUFFER_SIZE: int = 1024


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

    video_file_path: str = (
        "/home/haru/project/Recursion/VideoCompressorService/test/input/sample.mp4"
    )
    with open(video_file_path, 'rb') as video_file:
        while True:
            bytes_read = video_file.read(BUFFER_SIZE)
            if not bytes_read:
                break
            tcp_client.sendall(bytes_read)
    tcp_client.close()


if __name__ == "__main__":
    main()
