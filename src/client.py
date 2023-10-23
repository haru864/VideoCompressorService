import socket
import os


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
    buffer_size: int = 1024
    tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_client.connect((server_address, server_port))
    tcp_client.send(b"Data by TCP Client!!")
    response = tcp_client.recv(buffer_size)
    print("[*]Received a response : {}".format(response))


if __name__ == "__main__":
    main()
