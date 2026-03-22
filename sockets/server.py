import socket
import threading

host = '127.0.0.6'
port = 8888

russian_alphabet = "абвгдежзийклмнопрстуфхцчшщъыьэюя"

clients = {}
clients_lock = threading.Lock()


def transform_text(text):
    result = ""
    for char in text:
        lower_char = char.lower()

        if lower_char in russian_alphabet:
            index = russian_alphabet.index(lower_char)

            prev_chars = []
            for i in range(3, 0, -1):
                if index - i >= 0:
                    prev_chars.append(russian_alphabet[index - i])

            result += char.upper() + "".join(prev_chars)
        else:
            result += char

    return result


def send_user_list():
    with clients_lock:
        names = [data['name'] for data in clients.values()]
        connections = list(clients.keys())

    msg = f"SYS:USERS:{','.join(names)}\n"

    for conn in connections:
        try:
            conn.sendall(msg.encode('utf-8'))
        except:
            pass


def broadcast_system(message, sender_conn=None):
    with clients_lock:
        connections = list(clients.keys())

    for conn in connections:
        if conn == sender_conn:
            continue
        try:
            conn.sendall(f"SYS:MSG:{message}\n".encode('utf-8'))
        except:
            pass


def handle_client(conn, addr):
    buffer = ""
    client_name = None

    try:
        name_data = conn.recv(1024)
        if not name_data:
            return

        client_name = name_data.decode('utf-8').strip()

        with clients_lock:
            clients[conn] = {
                'name': client_name,
                'group': set()
            }

        print(f"[+] {client_name} подключился")

        send_user_list()

        conn.sendall(f"SYS:MSG:Добро пожаловать, {client_name}!\n".encode('utf-8'))

        broadcast_system(f"{client_name} вошёл в чат", conn)

        while True:
            data = conn.recv(1024)
            if not data:
                break

            buffer += data.decode('utf-8')

            while "\n" in buffer:
                message, buffer = buffer.split("\n", 1)
                message = message.strip()

                if not message:
                    continue

                if message.startswith("/"):
                    parts = message.split(" ", 1)
                    cmd = parts[0]

                    if cmd == "/group":
                        if len(parts) > 1:
                            names = [n.strip() for n in parts[1].split(",") if n.strip()]
                            with clients_lock:
                                clients[conn]['group'] = set(names)

                            conn.sendall(f"SYS:MSG:Группа: {', '.join(names)}\n".encode('utf-8'))
                        else:
                            with clients_lock:
                                clients[conn]['group'] = set()
                            conn.sendall("SYS:MSG:Группа сброшена\n".encode('utf-8'))

                    continue

                print(f"[{client_name}]: {message}")

                main_message = message
                extra_message = None

                if "<@>" in message:
                    parts = message.split("<@>", 1)
                    if len(parts) > 1:
                        text_to_transform = parts[1].strip()
                        if text_to_transform:
                            extra_message = transform_text(text_to_transform)

                with clients_lock:
                    sender_group = clients[conn]['group']
                    clients_copy = dict(clients)

                for c_conn, c_data in clients_copy.items():
                    if c_conn == conn:
                        continue

                    if sender_group and c_data['name'] not in sender_group:
                        continue

                    try:
                        msg = f"MSG:{client_name}:{main_message}\n"
                        c_conn.sendall(msg.encode('utf-8'))

                        if extra_message:
                            msg2 = f"MSG:{client_name}:[ПРЕОБРАЗОВАНО]: {extra_message}\n"
                            c_conn.sendall(msg2.encode('utf-8'))

                    except:
                        pass

                if extra_message:
                    conn.sendall(f"SYS:MSG:Преобразовано: {extra_message}\n".encode('utf-8'))

    except Exception as e:
        print(f"[!] Ошибка: {e}")

    finally:
        with clients_lock:
            if conn in clients:
                name = clients[conn]['name']
                del clients[conn]
                print(f"[-] {name} отключился")

        conn.close()
        send_user_list()
        broadcast_system(f"{client_name} вышел")


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.bind((host, port))
    except OSError:
        print("Ошибка: порт занят!")
        return

    s.listen()
    print(f"Сервер запущен {host}:{port}")

    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("Остановка сервера")
    finally:
        s.close()


if __name__ == "__main__":
    main()