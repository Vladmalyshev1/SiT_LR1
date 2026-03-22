import socket
import threading
import tkinter as tk
from tkinter import scrolledtext

HOST = '127.0.0.13'
PORT = 8888


class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("cleint")

        self.socket = None
        self.buffer = ""
        self.my_group = set()

        self.chat = scrolledtext.ScrolledText(root, state='disabled', height=20)
        self.chat.pack(fill="both", padx=10, pady=5)

        frame = tk.Frame(root)
        frame.pack(fill="x")

        tk.Label(frame, text="Пользователи (клик):").pack(anchor="w")

        self.users = tk.Listbox(frame, selectmode=tk.MULTIPLE, height=5)
        self.users.pack(fill="x")

        self.users.bind("<<ListboxSelect>>", self.update_group_from_ui)

        self.group_label = tk.Label(root, text="Общий чат", fg="blue")
        self.group_label.pack()

        bottom = tk.Frame(root)
        bottom.pack(fill="x", pady=5)

        self.entry = tk.Entry(bottom)
        self.entry.pack(side="left", fill="x", expand=True, padx=5)
        self.entry.bind("<Return>", self.send)

        tk.Button(bottom, text="➤", command=self.send).pack(side="right")

        self.connect()

    def write(self, msg):
        self.chat.config(state='normal')
        self.chat.insert(tk.END, msg + "\n")
        self.chat.config(state='disabled')
        self.chat.yview(tk.END)

    def connect(self):
        name = self.ask_name()

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((HOST, PORT))
            self.socket.sendall((name + "\n").encode())

            threading.Thread(target=self.receive, daemon=True).start()
            self.write("Подключено")

        except:
            self.write("Ошибка подключения")

    def ask_name(self):
        popup = tk.Toplevel(self.root)
        popup.title("Имя")

        tk.Label(popup, text="Введите имя").pack()
        entry = tk.Entry(popup)
        entry.pack()

        result = {"name": "Аноним"}

        def ok():
            result["name"] = entry.get().strip() or "Аноним"
            popup.destroy()

        tk.Button(popup, text="OK", command=ok).pack()
        self.root.wait_window(popup)

        return result["name"]

    def update_group_from_ui(self, event=None):
        selected = [self.users.get(i) for i in self.users.curselection()]
        self.my_group = set(selected)

        if self.my_group:
            self.group_label.config(text="Группа: " + ", ".join(self.my_group))
        else:
            self.group_label.config(text="Общий чат")

        try:
            if self.my_group:
                msg = "/group " + ",".join(self.my_group)
            else:
                msg = "/group"

            self.socket.sendall((msg + "\n").encode())
        except:
            pass

    def receive(self):
        try:
            while True:
                data = self.socket.recv(1024)
                if not data:
                    break

                self.buffer += data.decode()

                while "\n" in self.buffer:
                    msg, self.buffer = self.buffer.split("\n", 1)
                    self.process(msg)

        except:
            self.write("Соединение потеряно")

    def process(self, msg):
        if msg.startswith("SYS:USERS:"):
            users = msg.split(":", 2)[2].split(",")

            self.users.delete(0, tk.END)
            for u in users:
                if u:
                    self.users.insert(tk.END, u)

        elif msg.startswith("SYS:MSG:"):
            self.write("[СИСТЕМА] " + msg.split(":", 2)[2])

        elif msg.startswith("MSG:"):
            parts = msg.split(":", 2)
            if len(parts) >= 3:
                sender = parts[1]
                text = parts[2]

                if self.my_group and sender not in self.my_group:
                    return

                self.write(f"{sender}: {text}")

    def send(self, event=None):
        msg = self.entry.get().strip()
        if not msg:
            return

        try:
            self.socket.sendall((msg + "\n").encode())

            if not msg.startswith("/"):
                if self.my_group:
                    self.write(f"Вы → {', '.join(self.my_group)}: {msg}")
                else:
                    self.write(f"Вы → ВСЕ: {msg}")

        except:
            self.write("Ошибка отправки")

        self.entry.delete(0, tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClient(root)
    root.mainloop()