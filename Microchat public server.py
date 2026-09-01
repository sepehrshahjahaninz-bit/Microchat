from socket import socket, AF_INET, SOCK_STREAM, gethostbyname, gethostname, IPPROTO_TCP, TCP_NODELAY, SOL_SOCKET, SO_REUSEADDR, SHUT_WR
from threading import Thread, Lock
from json import dumps, loads
from os import path, makedirs, listdir
from collections import defaultdict
from time import time as time_now
from secrets import token_hex
import ssl

# basic configs for main app functions and server ports

VOICE_PORT = 2082
CHAT_PORT = 2052
SUB_REQUESTS_PORT = 2053
DESTRUCTOR_PASSWORD = 'nopassword'
HOST_ON = "0.0.0.0"
ROOMS_DIR = path.join(path.dirname(__file__), "rooms")
CERT_FILE = path.join(path.dirname(__file__), "cert.pem")
KEY_FILE = path.join(path.dirname(__file__), "key.pem")

# room creator rate limiter config

ROOMS_TO_ALLOW_AT_FIRST = 5
BASE_DELAY = 30
DELAY_MULTIPLIER = 2
MAXIMUM_ROOMS = 100

# message size settings

MAX_BUFFER_SIZE = 1024 * 1024

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
rooms = []
addrlist = []
client = False
voice_clients = {}
visiblerooms = []
message_histories = {}
voice_clients_lock = Lock()
roomlogs = defaultdict(list)
roomlock = Lock()
room_membership = {}
membership_lock = Lock()
room_tokens = {}
socket_client_ids = {}

try :
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
except Exception as e:
    print('Failed to load SSL context.\nError:', e)
    quit()

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
                        if room_id not in rooms:
                            rooms.append(room_id)
                        token = content.get("destruction_token")
                        if token:
                            room_tokens[room_id] = token
                    elif isinstance(content, list):
                        message_histories[room_id] = content
                        if room_id not in rooms:
                            rooms.append(room_id)
            except Exception:
                pass

def save_room_history(room_id,destruction_token):
    if is_room_destructed(room_id):
        return
    try:
        data = {
            "is_visible": room_id in visiblerooms,
            "destructed": False,
            "destruction_token": destruction_token,
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

def check_room_creation_allowed(ip):
    with roomlock:
        now = time_now()
        if len(rooms) >= MAXIMUM_ROOMS:
            return False, 0
        timestamps = roomlogs[ip]
        count = len(timestamps)
        if count < ROOMS_TO_ALLOW_AT_FIRST:
            return True, 0
        last = timestamps[-1]
        required_delay = BASE_DELAY * (DELAY_MULTIPLIER ** (count - ROOMS_TO_ALLOW_AT_FIRST))
        elapsed = now - last
        if elapsed >= required_delay:
            return True, 0
        return False, required_delay - elapsed

def record_room_creation(ip):
    with roomlock:
        roomlogs[ip].append(time_now())

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
            client_socket = ssl_context.wrap_socket(client_socket, server_side=True)
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
            if len(buffer) > MAX_BUFFER_SIZE:
                out_data = {
                    "message_type": "error",
                    "room_ID": chatID,
                    "error": "message_buffer_too_large",
                }
                client_socket.sendall((dumps(out_data) + "\n").encode("utf-8"))
                client_socket.close()
                return
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                data = loads(line)
                chatID = data.get("chat_id")
                msg_id = data.get("id")
                client_id = data.get("client_id")
                if is_room_destructed(chatID):
                    destruction_msg = (dumps({
                        "message_type": "error",
                        "error": "room_destroyed",
                        "room_ID": chatID,
                    }) + "\n").encode("utf-8")
                    client_socket.sendall(destruction_msg)
                    client_socket.close()
                    return
                if chatID not in rooms:
                    out_data = {
                        "message_type": "error",
                        "error": "room_does_not_exist",
                        "room_ID": chatID,
                        "id" : msg_id
                    }
                    client_socket.sendall((dumps(out_data) + "\n").encode("utf-8"))
                    client_socket.close()
                    return
                with membership_lock:
                    authorized_room = room_membership.get(client_id)
                if authorized_room != chatID:
                    out_data = {
                        "message_type": "error",
                        "error": "client_not_connected_to_room",
                        "room_ID": chatID,
                        "id": msg_id
                    }
                    client_socket.sendall((dumps(out_data) + "\n").encode("utf-8"))
                    client_socket.close()
                    return
                clientlist[client_socket] = chatID
                socket_client_ids[client_socket] = client_id
                msg = data.get("data")
                message_type = data.get("message_type")
                name = data.get("name")
                description = data.get("description", "none")
                time = data.get("time", "--:--")
                date = data.get("date", "--/--/----")
                client_id = data.get("client_id")
                msg_id = data.get("id")
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
                    "client_id": client_id,
                    "id": msg_id
                }
                message_histories[chatID].append(out_data)
                if len(message_histories[chatID]) > 100:
                    message_histories[chatID].pop(0)
                save_room_history(chatID, room_tokens.get(chatID))
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
        socket_client_ids.pop(client_socket, None)
        with membership_lock:
            room_membership.pop(client_id, None)
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
            client_socket = ssl_context.wrap_socket(client_socket, server_side=True)
            client_socket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
            Thread(target=handle_voice_client, args=(client_socket,), daemon=True).start()
    except Exception as x:
        print(f'Voice error: {x}')


def self_destruction_transmitter(client_socket, data):
    try:
        payloaddict = loads(data)
        password = payloaddict.get('password')
        room_ID = payloaddict.get('room_ID')
        token = payloaddict.get('token')
        out_data = {"request": "destruction", "room_ID": room_ID, "success": False}
        if password == DESTRUCTOR_PASSWORD and token == room_tokens.get(room_ID):
            if room_ID in visiblerooms:
                visiblerooms.remove(room_ID)
            if room_ID in rooms:
                rooms.remove(room_ID)
            mark_room_destructed(room_ID)
            message_histories.pop(room_ID, None)
            room_tokens.pop(room_ID, None)
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
        client_id = data_dict.get('client_id')
        with membership_lock:
            authorized_room = room_membership.get(client_id)
        if authorized_room != room_ID:
            out_data = {
                "request": "history",
                "room_ID": room_ID,
                "data": "client_not_connected_to_room"
            }
            client_socket.sendall((dumps(out_data) + "\n").encode("utf-8"))
            client_socket.close()
            return
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

def create_room(client_socket, data):
    try:
        ip = client_socket.getpeername()[0]
        room_to_make = data.get("room_id")
        VisibleOrNo = data.get("visible")
        client_id = data.get("client_id")
        allowed, wait_time = check_room_creation_allowed(ip)
        if not allowed:
            client_socket.sendall((dumps({
                "request": "create_room",
                "data": "rate_limited",
                "retry_after": round(wait_time, 1)
            }) + "\n").encode("utf-8"))
            client_socket.close()
            return
        elif not isinstance(room_to_make, str) or not room_to_make.isdigit():
            client_socket.sendall((dumps({
                "request": "create_room",
                "data": "room_id_invalid",
            }) + "\n").encode("utf-8"))
            client_socket.close()
            return
        elif len(room_to_make) != 7:
            client_socket.sendall((dumps({
                "request": "create_room",
                "data": "room_id_invalid",
            }) + "\n").encode("utf-8"))
            client_socket.close()
            return
        with membership_lock:
            if client_id in room_membership:
                client_socket.sendall((dumps({
                    "request": "create_room",
                    "data": "already_joined_a_room"
                }) + "\n").encode("utf-8"))
                client_socket.close()
                return
        if room_to_make in rooms:
            client_socket.sendall((dumps({
                "request": "create_room",
                "data": "room_id_already_exists"
            }) + "\n").encode("utf-8"))
            client_socket.close()
            return
        else:
            if VisibleOrNo == True:
                visiblerooms.append(room_to_make)
            rooms.append(room_to_make)
            message_histories[room_to_make] = []
            token = str(token_hex(16))
            room_tokens[room_to_make] = str(token)
            save_room_history(room_to_make,token)
            record_room_creation(ip)
            clientlist[client_socket] = room_to_make
            client_socket.sendall((dumps({
                "request": "create_room",
                "data": "room_created",
                "token": room_tokens.get(room_to_make)
            }) + "\n").encode("utf-8"))
            client_socket.close()
    except Exception as x:
        print(f"Create room error: {x}")
        try:
            client_socket.close()
        except Exception:
            pass

def join_room(client_socket, data):
    try:
        data_dic = loads(data)
        room_ID = data_dic.get("room_ID")
        client_id = data_dic.get("client_id")
        if not room_ID or not client_id:
            client_socket.sendall((dumps({
                "request": "join_room",
                "data": "incomplete_request"
            }) + "\n").encode("utf-8"))
            client_socket.close()
            return
        if is_room_destructed(room_ID) or room_ID not in rooms:
            client_socket.sendall((dumps({
                "request": "join_room",
                "room_ID": room_ID,
                "data": "room_does_not_exist"
            }) + "\n").encode("utf-8"))
            client_socket.close()
            return
        with membership_lock:
            if client_id in room_membership:
                client_socket.sendall((dumps({
                    "request": "join_room",
                    "room_ID": room_ID,
                    "data": "already_joined_a_room"
                }) + "\n").encode("utf-8"))
                client_socket.close()
                return
            room_membership[client_id] = room_ID
        client_socket.sendall((dumps({
            "request": "join_room",
            "room_ID": room_ID,
            "data": "joined_successfully",
        }) + "\n").encode("utf-8"))
        client_socket.close()
    except Exception as x:
        print(f"Join room error: {x}")
        try:
            client_socket.close()
        except:
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
        elif request == "create_room":
            create_room(client_socket,data)
        elif request == "join_room":
            join_room(client_socket,data)
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
            client_socket = ssl_context.wrap_socket(client_socket, server_side=True)
            client_socket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
            Thread(target=handle_sub_request, args=(client_socket,), daemon=True).start()
        except Exception as x:
            print(f"Sub request error: {x}")


Thread(target=voice_chat_server, daemon=True).start()
Thread(target=sub_request_handler, daemon=True).start()

accept_client_connection()