from socket import socket, AF_INET, SOCK_STREAM, gethostbyname, gethostname, IPPROTO_TCP, TCP_NODELAY, SOL_SOCKET, SO_REUSEADDR, SOCK_DGRAM, IPPROTO_UDP, SOL_IP, IP_ADD_MEMBERSHIP, IPPROTO_IP, INADDR_ANY, inet_aton
from threading import Thread, Lock
from json import dumps, loads
from time import localtime
import os
import struct

MCAST_PORT = 4488
PING_PORT = 2086
VOICE_PORT = 2082
CHAT_PORT = 2052
DESTRUCTION_LISTENER_PORT = 2053
PORT_MESSAGE_HISTORY = 2054
DESTRUCTOR_PASSWORD = 'ilikemicrochat2026'

ROOMS_DIR = os.path.join(os.path.dirname(__file__), "rooms_LAN")
if not os.path.exists(ROOMS_DIR):
    os.makedirs(ROOMS_DIR)

print('.........................................')

try:
    server = socket(AF_INET, SOCK_STREAM)
    server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', CHAT_PORT))
except Exception as x:
    print('\nCannot host likely due to port congestion.')
    print(x)
    quit()

clientlist = {}
addrlist = []
client = False
voice_clients = {}
visiblerooms = []
message_histories = {}
voice_clients_lock = Lock()


def is_room_destructed(room_id):
    filepath = os.path.join(ROOMS_DIR, f"room_{room_id}.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = loads(f.read())
                if isinstance(content, dict) and content.get("destructed", False):
                    return True
        except Exception:
            pass
    return False


def load_history_from_disk():
    for filename in os.listdir(ROOMS_DIR):
        if filename.startswith("room_") and filename.endswith(".json"):
            room_id = filename[5:-5]
            try:
                with open(os.path.join(ROOMS_DIR, filename), "r", encoding="utf-8") as f:
                    content = loads(f.read())
                    if isinstance(content, dict):
                        if content.get("destructed", False):
                            continue
                        message_histories[room_id] = content.get("history", [])
                        if content.get("is_visible", True) and room_id not in visiblerooms:
                            visiblerooms.append(room_id)
                    elif isinstance(content, list):
                        message_histories[room_id] = content
            except Exception:
                pass


def save_room_history(room_id):
    if is_room_destructed(room_id):
        return
    try:
        data = {
            "is_visible": room_id in visiblerooms,
            "destructed": False,
            "history": message_histories.get(room_id, [])
        }
        with open(os.path.join(ROOMS_DIR, f"room_{room_id}.json"), "w", encoding="utf-8") as f:
            f.write(dumps(data))
    except Exception:
        pass


def mark_room_destructed(room_id):
    filepath = os.path.join(ROOMS_DIR, f"room_{room_id}.json")
    history = message_histories.get(room_id, [])
    data = {
        "is_visible": False,
        "destructed": True,
        "history": history
    }
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(dumps(data))
    except Exception:
        pass


load_history_from_disk()


def send_line(sock, text: str):
    sock.sendall((text + "\n").encode("utf-8"))


def accept_client_connection():
    try:
        global addr
        server.listen()
        print(f'Server started successfully\nAddress : {gethostbyname(gethostname())}\n.........................................')
        print('\nWARNING : DO NOT CLOSE THIS WINDOW! CLOSING THIS WINDOW WILL SHUT DOWN THE HOST.\n')
    except Exception:
        pass
    while True:
        try:
            client_socket, addr = server.accept()
            clientlist[client_socket] = ''
            addrlist.append(addr)
            msgbrod = Thread(target=broadcast_message_to_client, args=(client_socket,), daemon=True)
            msgbrod.start()
        except Exception:
            pass


def broadcast_message_to_client(client_socket):
    try:
        active_rooms = list(set(clientlist.values()) | set(message_histories.keys()))
        initial_data = {
            "clients": active_rooms,
            "visible_rooms": visiblerooms 
        }
        client_socket.sendall((dumps(initial_data) + "\n").encode("utf-8"))
    except Exception as x:
        print(f"Failed to send initial data: {x}")
        client_socket.close()
        return

    buffer = ""

    while True:
        try:
            chunk = client_socket.recv(4096).decode("utf-8")
            if not chunk:
                break
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                data = loads(line)
                chatID = data["chat_id"]

                if is_room_destructed(chatID):
                    destruction_msg = (dumps({
                        "message_type": "room_destroyed",
                        "room_ID": chatID,
                        "room_destructed": True
                    }) + "\n").encode("utf-8")
                    client_socket.sendall(destruction_msg)
                    client_socket.close()
                    return

                msg = data["data"]
                idvisible = data["id_is_visible"]
                message_type = data["message_type"]
                name = data["name"]
                description = data["description"]

                if str(idvisible) == 'True' and chatID not in visiblerooms:
                    visiblerooms.append(chatID)
                clientlist[client_socket] = chatID

                if chatID not in message_histories:
                    message_histories[chatID] = []

                out_data = {
                    "message_type": message_type,
                    "data": msg,
                    "name": name,
                    "description": description,
                }

                message_histories[chatID].append(out_data)
                if len(message_histories[chatID]) > 100:
                    message_histories[chatID].pop(0)

                save_room_history(chatID)

                payload = (dumps(out_data) + "\n").encode("utf-8")

                if message_type == "text_message":
                    print(f"{chatID} {name} : \n{data['data']}")
                if message_type == "image_message":
                    print(f"{chatID} {name} : \n 1 image + {data['description']}")

                for c in list(clientlist.keys()):
                    if clientlist[c] == chatID:
                        try:
                            c.sendall(payload)
                        except Exception:
                            pass
        except Exception as x:
            print("Server error:", x)
            break

    try:
        client_socket.close()
        clientlist.pop(client_socket, None)
    except Exception:
        pass


def ping_server():
    try:
        s = socket(AF_INET, SOCK_STREAM)
        s.bind(('', PING_PORT))
        s.listen()
    except Exception as x:
        print(f'\nPing server encountered an error.\n{x}')
    while True:
        try:
            client_socket, addr = s.accept()
            client_socket.close()
        except Exception:
            pass


def handle_voice_client(client_socket):
    try:
        request = loads(client_socket.recv(1024).decode("utf-8"))
        chat_id = request["chat_id"]
        if is_room_destructed(chat_id):
            client_socket.close()
            return
        with voice_clients_lock:
            voice_clients[client_socket] = chat_id
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            with voice_clients_lock:
                sender_chat_id = voice_clients.get(client_socket)
                for c in voice_clients:
                    if c != client_socket and voice_clients[c] == sender_chat_id:
                        try:
                            c.sendall(data)
                        except Exception:
                            pass
    except Exception:
        pass
    with voice_clients_lock:
        if client_socket in voice_clients:
            del voice_clients[client_socket]
    client_socket.close()


def voice_chat_server():
    try:
        sock = socket(AF_INET, SOCK_STREAM)
        sock.bind(('', VOICE_PORT))
        sock.listen()
        while True:
            client_socket, addr = sock.accept()
            client_socket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1) 
            Thread(target=handle_voice_client, args=(client_socket,), daemon=True).start()
    except Exception as x:
        print(f'Voice error: {x}')


def self_destruction_transmitter():
    sock = socket(AF_INET, SOCK_STREAM)
    sock.bind(('', DESTRUCTION_LISTENER_PORT))
    sock.listen()
    while True:
        try:
            client_socket, addr = sock.accept()
            payload = client_socket.recv(1024).decode("utf-8")
            data = loads(payload)
            password = data.get('password')
            room_ID = data.get('room_ID')
            if password == DESTRUCTOR_PASSWORD:
                if room_ID in visiblerooms:
                    visiblerooms.remove(room_ID)
                mark_room_destructed(room_ID)
                message_histories.pop(room_ID, None)
                destruction_msg = (dumps({
                    "message_type": "room_destroyed",
                    "room_ID": room_ID,
                    "room_destructed": True
                }) + "\n").encode("utf-8")
                target_clients = [c for c, room in clientlist.items() if room == room_ID]
                for c in target_clients:
                    try:
                        c.sendall(destruction_msg)
                        c.close()
                    except Exception:
                        pass
                    if c in clientlist:
                        clientlist.pop(c, None)
                with voice_clients_lock:
                    target_voice = [vc for vc, room in voice_clients.items() if room == room_ID]
                    for vc in target_voice:
                        try:
                            vc.close()
                        except Exception:
                            pass
                        voice_clients.pop(vc, None)
            client_socket.close()
        except Exception as x:
            print(f"Destruction handler error: {x}")


def request_message_history():
    try:
        sock = socket(AF_INET, SOCK_STREAM)
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        sock.bind(('', PORT_MESSAGE_HISTORY))
        sock.listen()
    except Exception as x:
        print(f'\nMessage history server encountered an error.\n{x}')
        return
    while True:
        try:
            client_socket, addr = sock.accept()
            in_data = client_socket.recv(1024).decode("utf-8")
            if not in_data:
                client_socket.close()
                continue
            data_dict = loads(in_data.strip())
            room_ID = data_dict.get('room_ID')
            if is_room_destructed(room_ID):
                out_data = {"room_ID": room_ID, "history": [], "destructed": True}
                client_socket.sendall((dumps(out_data) + "\n").encode("utf-8"))
            elif room_ID in message_histories:
                history = message_histories[room_ID]
                out_data = {
                    "room_ID": room_ID,
                    "history": history
                }
                client_socket.sendall((dumps(out_data) + "\n").encode("utf-8"))
            else:
                out_data = {"room_ID": room_ID, "history": []}
                client_socket.sendall((dumps(out_data) + "\n").encode("utf-8"))
            client_socket.close()
        except Exception as e:
            print(f"History request error: {e}")


def finder():
    global MCAST_PORT
    MCAST_GRP = '239.255.255.250'
    s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    s.bind(('', MCAST_PORT))
    mreq = struct.pack("4sl", inet_aton(MCAST_GRP), INADDR_ANY)
    s.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP, mreq)
    while True:
        data, addr = s.recvfrom(1024)
        if data == b'//*LOOKING FOR SERVER//*':
            s.sendto(b'//*SERVER IS HERE//*', addr)


Thread(target=voice_chat_server, daemon=True).start()
Thread(target=ping_server, daemon=True).start()
Thread(target=self_destruction_transmitter, daemon=True).start()
Thread(target=request_message_history, daemon=True).start()
Thread(target=finder, daemon=True).start()

accept_client_connection()