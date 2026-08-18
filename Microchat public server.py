from socket import socket, AF_INET, SOCK_STREAM, gethostbyname, gethostname, IPPROTO_TCP, TCP_NODELAY, SOL_SOCKET, SO_REUSEADDR, SHUT_WR
from threading import Thread, Lock
from json import dumps, loads
from os import path, makedirs, listdir

VOICE_PORT = 2082
CHAT_PORT = 2052
SUB_REQUESTS_PORT = 2053
DESTRUCTOR_PASSWORD = 'nopassword'
HOST_ON = "0.0.0.0"

ROOMS_DIR = path.join(path.dirname(__file__), "rooms")
if not path.exists(ROOMS_DIR):
    makedirs(ROOMS_DIR)

print('.........................................')

try:
    server = socket(AF_INET, SOCK_STREAM)
    server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server.bind((HOST_ON, CHAT_PORT))
except Exception as x:
    print('\nCannot host likely due to port congestion.')
    print(x)
    quit()

clientlist = {}
typingclientlist = {}
addrlist = []
client = False
voice_clients = {}
visiblerooms = []
message_histories = {}
voice_clients_lock = Lock()


def is_room_destructed(room_id):
    filepath = path.join(ROOMS_DIR, f"room_{room_id}.json")
    if path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = loads(f.read())
                if isinstance(content, dict) and content.get("destructed", False):
                    return True
        except Exception:
            pass
    return False


def load_history_from_disk():
    for filename in listdir(ROOMS_DIR):
        if filename.startswith("room_") and filename.endswith(".json"):
            room_id = filename[5:-5]
            try:
                with open(path.join(ROOMS_DIR, filename), "r", encoding="utf-8") as f:
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
        with open(path.join(ROOMS_DIR, f"room_{room_id}.json"), "w", encoding="utf-8") as f:
            f.write(dumps(data))
    except Exception:
        pass


def mark_room_destructed(room_id):
    filepath = path.join(ROOMS_DIR, f"room_{room_id}.json")
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
                time = data["time"]
                date = data["date"]
                client_id = data["client_id"]
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
                    "time": time,
                    "date": date,
                    "client_id": client_id
                }
                message_histories[chatID].append(out_data)
                if len(message_histories[chatID]) > 100:
                    message_histories[chatID].pop(0)
                save_room_history(chatID)
                payload = (dumps(out_data) + "\n").encode("utf-8")
                if message_type == "text_message":
                    print(f"{time} - {date} {chatID} {name} : \n{data['data']}")
                if message_type == "image_message":
                    print(f"{time} - {date} {chatID} {name} : \n 1 image + {data['description']}")
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
        sock.bind((HOST_ON, VOICE_PORT))
        sock.listen()
        while True:
            client_socket, addr = sock.accept()
            client_socket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
            Thread(target=handle_voice_client, args=(client_socket,), daemon=True).start()
    except Exception as x:
        print(f'Voice error: {x}')


def self_destruction_transmitter(client_socket, data):
    try:
        payloaddict = loads(data)
        password = payloaddict.get('password')
        room_ID = payloaddict.get('room_ID')
        out_data = {"request": "destruction", "room_ID": room_ID, "success": False}
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
                    try:
                        c.shutdown(SHUT_WR)
                    except Exception:
                        pass
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
            out_data["success"] = True
        try:
            client_socket.sendall((dumps(out_data) + "\n").encode("utf-8"))
        except Exception:
            pass
        client_socket.close()
    except Exception as x:
        print(f"Destruction handler error: {x}")
        try:
            client_socket.close()
        except Exception:
            pass

def request_message_history(client_socket, data):
    try:
        in_data = data
        if not in_data:
            client_socket.close()
            return
        data_dict = loads(in_data.strip())
        room_ID = data_dict.get('room_ID')
        if is_room_destructed(room_ID):
            out_data = {"request": "history", "room_ID": room_ID, "history": [], "destructed": True}
        elif room_ID in message_histories:
            out_data = {"request": "history", "room_ID": room_ID, "history": message_histories[room_ID]}
        else:
            out_data = {"request": "history", "room_ID": room_ID, "history": []}
        client_socket.sendall((dumps(out_data) + "\n").encode("utf-8"))
        client_socket.close()
    except Exception as e:
        print(f"History request error: {e}")
        try:
            client_socket.close()
        except Exception:
            pass

def process_typing_update(client, data):
    try:
        data_dict = loads(data)
        room_ID = data_dict.get('room_ID')
        name = data_dict.get('name')
        typing = data_dict.get('typing')
        client_id = data_dict.get('client_id')
        if room_ID is None or client_id is None:
            return None
        if is_room_destructed(room_ID):
            return None
        old = typingclientlist.get(client_id, {}).get("socket") if client_id else None
        if old and old is not client:
            try:
                old.close()
            except Exception:
                pass
        typingclientlist[client_id] = {"socket": client, "room_ID": room_ID}
        payload = (dumps({
            "request": "typing",
            "room_ID": room_ID,
            "name": name,
            "typing": typing,
            "client_id": client_id
        }) + "\n").encode("utf-8")
        for cid, info in list(typingclientlist.items()):
            if info["room_ID"] == room_ID and cid != client_id:
                try:
                    info["socket"].sendall(payload)
                except Exception:
                    try:
                        info["socket"].close()
                    except Exception:
                        pass
                    typingclientlist.pop(cid, None)
        return client_id
    except Exception as x:
        print(f"Typing update error: {x}")
        return None


def handle_typing_client(client, data):
    client_id = None
    try:
        client_id = process_typing_update(client, data)
        buffer = ""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            buffer += chunk.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    outer = loads(line)
                except Exception:
                    continue
                if outer.get("request") != "typing":
                    continue
                cid = process_typing_update(client, outer.get("data"))
                if cid:
                    client_id = cid
    except Exception as x:
        print(f"Typing listener error: {x}")
    finally:
        try:
            if client_id and typingclientlist.get(client_id, {}).get("socket") is client:
                typingclientlist.pop(client_id, None)
            client.close()
        except Exception:
            pass

def send_available_rooms(client_socket):
    global visiblerooms
    try:
        client_socket.sendall((dumps({
            "request": "available_rooms",
            "data": [visiblerooms, list(set(clientlist.values()))]
        }) + "\n").encode("utf-8"))
    except Exception as x:
        print(f"Available rooms transmission error: {x}")
        try:
            client_socket.close()
        except Exception:
            pass

def handle_sub_request(client_socket):
    try:
        payload = client_socket.recv(1024).decode("utf-8")
        if not payload:
            client_socket.close()
            return
        payloaddict = loads(payload.strip())
        request = payloaddict.get("request")
        data = payloaddict.get("data")
        if request == "destruction":
            self_destruction_transmitter(client_socket, data)
        elif request == "history":
            request_message_history(client_socket, data)
        elif request == "typing":
            handle_typing_client(client_socket, data)
        elif request == "ping":
            client_socket.close()
        elif request == "available_rooms":
            send_available_rooms(client_socket)
        else:
            client_socket.close()
    except Exception as x:
        print(f"Sub request dispatch error: {x}")
        try:
            client_socket.close()
        except Exception:
            pass


def sub_request_handler():
    try:
        sock = socket(AF_INET, SOCK_STREAM)
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        sock.bind((HOST_ON, SUB_REQUESTS_PORT))
        sock.listen()
    except Exception as x:
        print(f'\nSub request server encountered an error.\n{x}')
        return
    while True:
        try:
            client_socket, addr = sock.accept()
            client_socket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
            Thread(target=handle_sub_request, args=(client_socket,), daemon=True).start()
        except Exception as x:
            print(f"Sub request error: {x}")


Thread(target=voice_chat_server, daemon=True).start()
Thread(target=sub_request_handler, daemon=True).start()

accept_client_connection()