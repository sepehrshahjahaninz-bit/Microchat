from socket import socket,AF_INET,SOCK_STREAM,gethostbyname,gethostname,IPPROTO_TCP,TCP_NODELAY, SOL_SOCKET, SO_REUSEADDR
from threading import Thread,Lock
from json import dumps,loads

PING_PORT = 2086
VOICE_PORT = 2082
CHAT_PORT = 2052

print('.........................................')

try :
    server = socket(AF_INET,SOCK_STREAM)
    server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server.bind(('0.0.0.0',CHAT_PORT))
except Exception as x:
    print('\nCannot host likely due to port congestion.')
    print(x)
    quit()

clientlist={}
addrlist=[]
client = False
voice_clients = {}
visiblerooms = []
voice_clients_lock = Lock()

def accept_client_connection() : 
    try :
        global addr,BROWSER_REDIRECT_LINK
        server.listen()
        print(f'Server started succesfully\nAddress : {gethostbyname(gethostname())}\n.........................................')
        print('\nWARNING : DO NOT CLOSE THIS WINDOW! CLOSING THIS WINDOW WILL SHUT DOWN THE HOST.\n')
    except :
        pass
    while True :
        try :
            client, addr = server.accept()
            active_rooms = list(set(clientlist.values())) 
            data = {
                "clients": active_rooms,
                "visible_rooms": visiblerooms
            }
            client.sendall(dumps(data).encode("utf-8"))
            clientlist[client] = ''
            addrlist.append(addr)
            msgbrod = Thread(target = broadcast_message_to_client, args = (client,), daemon = True)
            msgbrod.start()
        except :
            pass

def broadcast_message_to_client(client) :
    try:
        active_rooms = list(set(clientlist.values())) 
        data = {
            "clients": active_rooms,
            "visible_rooms": visiblerooms
        }
        client.sendall(dumps(data).encode("utf-8"))
    except Exception as x:
        print(f"Failed to send initial data: {x}")
        client.close()
        return
    while True:
        try :
            raw_data = client.recv(1024)
            if not raw_data:
                break
            data = loads(raw_data.decode("utf-8"))
            chatID = data["chat_id"]
            msg = data["message"]
            idvisible = data["id_is_visible"]
            if str(idvisible) == 'True' and chatID not in visiblerooms :
                visiblerooms.append(chatID)
            clientlist[client] = chatID
            for c in clientlist :
                if clientlist[c] == chatID :
                    c.send(f'{msg}'.encode('utf-8'))
        except Exception as x:
            print(x)
            break
    try :
        client.close()
        if client in clientlist:
            clientlist.pop(client)
    except:
        pass

def ping_server():
    try :
        s=socket(AF_INET,SOCK_STREAM)
        s.bind(('',PING_PORT))
        s.listen()
    except Exception as x:
        print(f'\nPing server encountered an error.\n{x}')
    while True :
        try :
            client, addr = s.accept()
            client.close()
        except :
            pass

def handle_voice_client(client_socket):
    try:
        request = loads(client_socket.recv(1024).decode("utf-8"))
        chat_id = request["chat_id"]
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
                        except:
                            pass
    except:
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
            client, addr = sock.accept()
            client.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1) 
            Thread(target=handle_voice_client, args=(client,), daemon=True).start()
    except Exception as x:
        print(f'Voice error: {x}')

Thread(target = voice_chat_server).start()
Thread(target = ping_server).start()

accept_client_connection()