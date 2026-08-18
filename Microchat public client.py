from socket import socket, AF_INET, SOCK_STREAM, IPPROTO_TCP, TCP_NODELAY
from tkinter.messagebox import showerror, showwarning, askyesnocancel, askyesno
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from time import time, sleep, localtime
from pyautogui import password
from threading import Thread, Event as T_Event
from random import choice
from queue import Queue
from pyaudio import PyAudio, paInt32
from json import loads, dumps
from base64 import b64encode, b64decode
from PIL import Image, ImageTk
from io import BytesIO
from uuid import uuid4
from os import path
from sys import platform
from queue import Queue, Empty

WIDTH, HEIGHT = 680, 550
HOST = "127.0.0.1"
PORT_CHAT = 2052
PORT_VOICE = 2082
PORT_SUB_REQUESTS = 2053
CONFIG_FILE = path.join(path.dirname(__file__), "config.json")
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2

Connect = 0
nickname = ''
chatID = ''
alreadysending = False
audio_enabled = False
voice_enabled = False
id_visible = None
connectedormaderoom = None
noinputoutput = False
image_attached = False
attached_image = None
chat_destroyed = False
typesock = None
muted = False
saved_nickname = ""
uploading_image = False
active_typers = {}
previous_visibleroomslist = []
visiblerooms = []
availableclies = {}
pending_messages = {}
pending_messages = {}
pending_message_data = {}
message_retry_count = {}
send_queue = Queue()

if platform == "win32":
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(0)
    except Exception:
        pass

root = Tk()
root.withdraw()
root.title('μChat')
root.geometry(f'{WIDTH}x{HEIGHT}')
root.config(background='light gray')
root.resizable(False, False)
root.tk.call('tk', 'scaling', 2.0)

try:
    client = socket(AF_INET, SOCK_STREAM)
    client.settimeout(5)
    client.connect((HOST, PORT_CHAT))
except Exception as e:
    showerror(title='μChat', message=f'Cannot connect to server.\nErr : {e}')
    quit()

try:
    audio_queue = Queue()
    p = PyAudio()
    CHUNK = 512
    FORMAT = paInt32
    CHANNELS = 2
    RATE = 48000
    input_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    output_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
    noinputoutput = False
except:
    showwarning(title='μChat', message='No Audio input/output device detected! Voice chat is unavailable.')
    noinputoutput = True

if not noinputoutput:
    try:
        voicesocket = socket(AF_INET, SOCK_STREAM)
        voicesocket.connect((HOST, PORT_VOICE))
        voicesocket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        client.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        data = {
            "chat_id": chatID,
        }
        voicesocket.sendall(dumps(data).encode("utf-8"))
    except Exception as e:
        showerror(title='μChat', message='Voice chat failed to connect.\nThe chat may still work.')

if path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            config = loads(f.read())
            client_id = config.get("client_id")
            saved_nickname = config.get("nickname")
            if not client_id:
                raise ValueError("client_id key missing")
    except Exception:
        client_id = str(uuid4())
        with open(CONFIG_FILE, "w") as f:
            f.write(dumps({"client_id": client_id, "nickname": saved_nickname}, indent=4))
else:
    client_id = str(uuid4())
    with open(CONFIG_FILE, "w") as f:
        f.write(dumps({"client_id": client_id, "nickname": saved_nickname}, indent=4))

def create_an_ID(availableclies):
    data = [0,1,2,3,4,5,6,7,8,9]
    nickname = str(choice(data))
    for i in range(6):
        nickname = nickname + str(choice(data))
    while nickname in availableclies:
        nickname = create_an_ID(availableclies)
        return
    return nickname

def save_nickname(nickname):
    global saved_nickname
    saved_nickname = nickname
    try:
        with open(CONFIG_FILE, "w") as f:
            f.write(dumps({"client_id": client_id, "nickname": saved_nickname}, indent=4))
    except Exception as e:
        showerror(title='μChat', message=f'Can\'t save nickname.\n{e}')

def mark_message_sent(msg_id):
    info = pending_messages.pop(msg_id, None)
    pending_message_data.pop(msg_id, None)
    message_retry_count.pop(msg_id, None)
    if not info:
        return
    try:
        if info["bar"]:
            info["bar"].stop()
            info["bar"].destroy()
        info["label"].config(text="Sent", fg='gray', font=('Arial', 6, 'italic'))
    except TclError:
        pass

def mark_message_failed(msg_id, err):
    info = pending_messages.get(msg_id)
    if not info:
        return
    retries = message_retry_count.get(msg_id, 0)
    if retries < MAX_RETRIES:
        message_retry_count[msg_id] = retries + 1
        try:
            info["label"].config(text=f"Retrying ({retries+1}/{MAX_RETRIES})", fg='orange', font=('Arial', 6, 'italic'))
        except TclError:
            pass
        delay_ms = int(RETRY_BASE_DELAY * (2 ** retries) * 1000)
        root.after(delay_ms, retry_send, msg_id)
    else:
        pending_messages.pop(msg_id, None)
        pending_message_data.pop(msg_id, None)
        message_retry_count.pop(msg_id, None)
        try:
            if info["bar"]:
                info["bar"].stop()
                info["bar"].destroy()
            info["label"].config(text="Failed to deliver", fg='red', font=('Arial', 6, 'italic'))
        except TclError:
            pass

def retry_send(msg_id):
    if chat_destroyed:
        return
    data = pending_message_data.get(msg_id)
    info = pending_messages.get(msg_id)
    if not data or not info:
        return
    try:
        info["label"].config(text="Delivering", fg='gray', font=('Arial', 7, 'italic'))
    except TclError:
        pass
    send_queue.put((msg_id, data))

def sender_worker():
    while True:
        item = send_queue.get()
        if item is None:
            break
        msg_id, data = item
        try:
            client.sendall((dumps(data) + "\n").encode("utf-8"))
        except Exception as e:
            root.after(0, mark_message_failed, msg_id, str(e))
        send_queue.task_done()

def image_uploading_loading_bar():
    global upload_window, upload_bar
    upload_window = Toplevel(root)
    upload_window.title('μChat')
    upload_window.geometry('300x100')
    upload_window.resizable(False, False)
    upload_window.grab_set()
    upload_bar = ttk.Progressbar(upload_window, orient=HORIZONTAL, length=300, mode='indeterminate')
    upload_bar.place(x=0, y=30)
    upload_bar.start(15)

def close_upload_bar():
    global upload_window, upload_bar
    try:
        upload_bar.stop()
        upload_window.destroy()
    except Exception:
        pass

def validate(id=None, logindiag=None, idfield=None, nicknamefield=None, id_visible_var=None):
    global chatID, nickname, id_visible, connectedormaderoom, availableclies, visiblerooms
    if id is None:
        r_id = idfield.get().strip()
    else:
        r_id = id
    nick = nicknamefield.get().strip()
    if not r_id:
        showerror(title='μChat', message='Room ID cannot be empty.', parent=logindiag)
        return
    if not nick:
        showerror(title='μChat', message='Nickname cannot be empty.', parent=logindiag)
        return
    if r_id in visiblerooms or r_id in availableclies:
        chatID = r_id
        nickname = nick
        connectedormaderoom = True
        id_visible = id_visible_var.get()
        save_nickname(nick)
        logindiag.destroy()
    else:
        showerror(title='μChat', message='Invalid Room ID.', parent=logindiag)

def update_available_rooms(max_per_column, inner_frame, logindiag, idfield, nicknamefield, id_visible_var):
    global visiblerooms, previous_visibleroomslist, availableclies
    result_queue = Queue()
    stop_event = T_Event()
    def resquester():
        while not stop_event.is_set():
            try:
                searchsock = socket(AF_INET, SOCK_STREAM)
                searchsock.settimeout(3)
                searchsock.connect((HOST, PORT_SUB_REQUESTS))
                searchsock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
                searchsock.sendall((dumps({"request": "available_rooms"}) + "\n").encode("utf-8"))
                raw_inp = searchsock.recv(65536).decode("utf-8")
                searchsock.close()
                result = loads(raw_inp.strip()).get("data")
                roomsfound = result[0]
                availableclies = result[1]
                if roomsfound is not None:
                    result_queue.put(("data", roomsfound))
            except Exception as x:
                if not stop_event.is_set():
                    result_queue.put(("error", str(x)))
                return
            stop_event.wait(1)
    def update_list(rooms):
        global visiblerooms, previous_visibleroomslist
        if rooms == visiblerooms:
            return
        previous_visibleroomslist = rooms
        visiblerooms = rooms
        try:
            if not logindiag.winfo_exists():
                return
            for widget in inner_frame.winfo_children():
                widget.destroy()
            for index, room in enumerate(rooms):
                current_col = index // max_per_column
                current_row = index % max_per_column
                roomslistbox = Frame(inner_frame, bg='white')
                roomlabel = Label(roomslistbox, text=room, font=("Arial", 10), bg="white", fg='black', wraplength=100)
                joinbtn = Button(roomslistbox, command=lambda r=room: (stop_event.set(), validate(r, logindiag, idfield, nicknamefield, id_visible_var)), text="Join", font=("Arial", 8), fg='white', bg='green', width=6)
                roomlabel.pack(side=LEFT, padx=(0, 2))
                joinbtn.pack(side=LEFT)
                roomslistbox.grid(row=current_row, column=current_col, sticky=W, padx=8, pady=2)
            if rooms == []:
                Label(inner_frame, text="No rooms are currently listed publicly.\nClick cancel and press create room\nto make a new one!", anchor=W, justify=LEFT, font=("Arial", 10), fg='black', bg="white", wraplength=400).pack(anchor=W, padx=10)
            logindiag.update_idletasks()
        except TclError:
            stop_event.set()
    def check_queue():
        if not logindiag.winfo_exists():
            stop_event.set()
            return
        try:
            while True:
                kind, payload = result_queue.get_nowait()
                if kind == "data":
                    update_list(payload)
                elif kind == "error":
                    if logindiag.winfo_exists():
                        showerror(title='μChat', message=f"Can't update available rooms.\n{payload}")
                    stop_event.set()
                    return
        except Empty:
            pass
        except TclError:
            stop_event.set()
            return
        if logindiag.winfo_exists() and not stop_event.is_set():
            logindiag.after(200, check_queue)
    Thread(target=resquester, daemon=True).start()
    logindiag.after(200, check_queue)
    return stop_event

def show_login_dialog():
    global chatID, nickname, id_visible, connectedormaderoom, saved_nickname
    a = askyesnocancel(title='μChat', message='Do you want to join a chat? Click No to create a new room.')
    if a is None:
        quit()
    logindiag = Toplevel(root)
    logindiag.title('μChat')
    logindiag.geometry('460x250')
    logindiag.resizable(False, False)
    if a is True:
        toplabel = Label(logindiag, text="Choose a room to join or enter the room ID.", font=("Arial", 10), fg='black', wraplength=400)
        toplabel.pack(anchor=W, padx=10, pady=(5, 0))
        container = Frame(logindiag, width=440, height=160, bg='white')
        container.pack(anchor=W, padx=10, pady=5)
        container.pack_propagate(False)
        roomlistcanvas = Canvas(container, highlightthickness=0, bg='white')
        def scroll_handler(*args):
            if args[0] == 'moveto':
                roomlistcanvas.yview_moveto(args[1])
            elif args[0] == 'scroll':
                roomlistcanvas.yview_scroll(int(args[1]), args[2])
        v_scrollbar = Scrollbar(container, orient="vertical", command=scroll_handler)
        roomlistcanvas.configure(yscrollcommand=v_scrollbar.set)
        inner_frame = Frame(roomlistcanvas, bg='white')
        inner_frame.bind("<Configure>", lambda e: roomlistcanvas.configure(scrollregion=roomlistcanvas.bbox("all")))
        roomlistcanvas.create_window((0, 0), window=inner_frame, anchor="nw")
        v_scrollbar.pack(side=RIGHT, fill=Y)
        roomlistcanvas.pack(side=LEFT, fill=BOTH, expand=True)
        max_per_column = 10
        Label(logindiag, text="Room ID:", font=("Arial", 10), fg='black').pack(anchor=W, padx=10)
        idfield = Entry(logindiag, width=50)
        idfield.pack(anchor=W, padx=10)
        idfield.focus()
        Label(logindiag, text="Nickname:").pack(anchor=W, padx=10)
        nicknamefield = Entry(logindiag, width=50)
        nicknamefield.pack(anchor=W, padx=10)
        if saved_nickname:
            nicknamefield.insert(0, saved_nickname)
        id_visible_var = BooleanVar(value=True)
        btn_frame = Frame(logindiag)
        btn_frame.pack(fill='x', pady=10)
        Button(btn_frame, text="Join", command=lambda: validate(None, logindiag, idfield, nicknamefield, id_visible_var), bg="green", fg="white", width=10).pack(side="left", padx=15)
        Button(btn_frame, text="Cancel", command=lambda: (logindiag.destroy(), quit()), bg="red", fg="white", width=10).pack(side="right", padx=15)
        update_available_rooms(max_per_column, inner_frame, logindiag, idfield, nicknamefield, id_visible_var)
        logindiag.update_idletasks()
        needed_height = max(250, logindiag.winfo_reqheight())
        logindiag.geometry(f'460x{needed_height}')
    else:
        logindiag.geometry('300x200')
        toplabel = Label(logindiag, text="Create a new room", font=("Arial", 10, "bold"), fg='black')
        toplabel.pack(anchor=W, padx=10, pady=(5, 0))
        Label(logindiag, text="Nickname:").pack(anchor=W, padx=10, pady=(5, 0))
        nicknamefield = Entry(logindiag, width=30)
        nicknamefield.pack(anchor=W, padx=10)
        if saved_nickname:
            nicknamefield.insert(0, saved_nickname)
        nicknamefield.focus()
        id_visible_var = BooleanVar(value=True)
        Checkbutton(logindiag, text="Room visible publicly", variable=id_visible_var).pack(anchor=W, padx=10, pady=5)
        def create_room():
            global chatID, nickname, id_visible, connectedormaderoom
            nick = nicknamefield.get().strip()
            if not nick:
                showerror(title='μChat', message='Nickname cannot be empty.', parent=logindiag)
                return
            visible = id_visible_var.get()
            max_attempts = 10
            result = None
            for attempt in range(max_attempts):
                new_id = create_an_ID(availableclies)
                try:
                    sock = socket(AF_INET, SOCK_STREAM)
                    sock.settimeout(5)
                    sock.connect((HOST, PORT_SUB_REQUESTS))
                    sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
                    payload = {
                        "request": "create_room",
                        "data": {"room_id": new_id, "visible": visible}
                    }
                    sock.sendall((dumps(payload) + "\n").encode("utf-8"))
                    buffer = ""
                    while "\n" not in buffer:
                        chunk = sock.recv(4096).decode("utf-8")
                        if not chunk:
                            break
                        buffer += chunk
                    sock.close()
                    result = loads(buffer.strip())
                except Exception as e:
                    showerror(title='μChat', message=f"Couldn't create room.\n{e}", parent=logindiag)
                    return
                if result.get("data") == "room_created":
                    chatID = new_id
                    nickname = nick
                    id_visible = visible
                    connectedormaderoom = False
                    save_nickname(nick)
                    logindiag.destroy()
                    return
                elif result.get("data") == "room_id_already_exists":
                    continue
                elif result.get("data") == "rate_limited":
                    showerror(title='μChat', message=f"You have attempted to create too many rooms.\nTry again in {result.get('retry_after')} seconds.", parent=logindiag)
                    return
                elif result.get("data") == "room_id_invalid":
                    showerror(title='μChat', message=f"The generated Room ID is invalid or incompatible to the server.")
                    return
                else:
                    showerror(title='μChat', message=f"Couldn't create room.\n{result.get('data')}", parent=logindiag)
                    return
            showerror(title='μChat', message="Couldn't create a unique room ID.", parent=logindiag)
            return
        btn_frame = Frame(logindiag)
        btn_frame.pack(fill='x', pady=10)
        Button(btn_frame, text="Create", command=create_room, bg="green", fg="white", width=10).pack(side="left", padx=15)
        Button(btn_frame, text="Cancel", command=lambda: (logindiag.destroy(), quit()), bg="red", fg="white", width=10).pack(side="right", padx=15)
    root.wait_window(logindiag)

def gettimestamp():
    return f"{localtime()[3]}:{localtime()[4]}:{localtime()[5]}"

def getdatestamp():
    return f"{localtime()[2]}/{localtime()[1]}/{localtime()[0]}"

while not (chatID and nickname):
    show_login_dialog()

root.deiconify()

try:
    data = {
        "chat_id": chatID,
        "id_is_visible": id_visible,
        "data": 'connected',
        "message_type": "text_message",
        "name": nickname,
        "description": "none",
        "time" : gettimestamp(),
        "date" : getdatestamp(),
        "client_id" : client_id,
        "id": str(uuid4())
    }
    client.sendall((str(dumps(data)) + "\n").encode("utf-8"))
except Exception as e:
    showerror(title='μChat', message='Can\'t connect.\nError:' + str(e))
    quit()

def errorsign():
    root.config(bg='red')
    autoscchbx.config(bg='red')
    sticktocorner.config(bg='red')
    headertxt.config(bg='red')
    headertxt.config(fg='black')
    sleep(0.1)
    root.config(bg='light grey')
    autoscchbx.config(bg='light grey')
    sticktocorner.config(bg='light grey')
    headertxt.config(bg='light grey')
    headertxt.config(fg='green')
    ymstbx.delete(1.0, END)
    ymstbx.focus()

def clear_chat_frame():
    for widget in tbxmain.winfo_children():
        widget.destroy()
    update_scroll()

def copy_to_clipboard(text):
    root.clipboard_clear()
    root.clipboard_append(text) 

def del_message(bubble_frame):
    choice = askyesno(title='μChat', message='Are you sure you want to delete this message for yourself?\nThis action only removes the messsage from current session\nand can be restored using load history.')
    if choice:
        bubble_frame.destroy()
    else:
        return

def save_image(image):
    filename = filedialog.asksaveasfilename(
        title="Save Image",
        defaultextension=".png",
        filetypes=[
            ("PNG Image", "*.png"),
            ("JPEG Image", "*.jpg;*.jpeg"),
            ("Bitmap Image", "*.bmp"),
            ("All Files", "*.*")
        ],
        initialfile=f"microchat_image.png"
    )
    if not filename:
        return
    try:
        if filename.lower().endswith(('.jpg', '.jpeg')) and image.mode in ('RGBA', 'LA'):
            converted_img = Image.new("RGB", image.size, (255, 255, 255))
            converted_img.paste(image, mask=image.split()[-1])
            converted_img.save(filename)
        else:
            image.save(filename)
    except Exception as e:
        showerror(title='μChat', message=f"Failed to save image:\n{e}")

def remove_failed_message(msg_id):
    info = pending_messages.pop(msg_id, None)
    pending_message_data.pop(msg_id, None)
    message_retry_count.pop(msg_id, None)
    if not info:
        return
    try:
        if info["bar"]:
            info["bar"].stop()
            info["bar"].destroy()
        frame = info.get("frame")
        if frame:
            bubble = frame.master
            bubble.destroy()
        update_scroll()
    except TclError:
        pass

def create_new_message_bubble(message, message_type, name, description="", time="--:--",date="--/--/----", client_id_num="unknown", msg_id=None, pending=False):
    global client_id
    if message_type == "text_message":
        text = f"{message}"
        anchor=W
        bg_color = 'light blue'
        if client_id_num == client_id:
            bg_color = 'light green'
            anchor = E
        else:
            bg_color = 'light blue'
            anchor = W
        bubble_frame = Frame(tbxmain, bg=bg_color, width=620)
        name_label = Label(bubble_frame, text=name, fg='black', bg=bg_color, font=('Arial', 8, 'bold'), anchor=W)
        name_label.pack(pady=(5, 0), padx=5, anchor=W)
        message_label = Label(bubble_frame, text=text, fg='black', bg=bg_color, anchor=W, wraplength=580, justify=LEFT)
        message_label.pack(pady=5, padx=5, anchor=W)
        btn_frame = Frame(bubble_frame, bg=bg_color)
        copybtn = Button(btn_frame, text="COPY", command=lambda: copy_to_clipboard(text), bg="green", fg="white", width=6, height=1,font=('Arial', 6, 'bold'))
        delbtn = Button(btn_frame, text="DELETE", command=lambda: (pending_messages.pop(msg_id, None),pending_message_data.pop(msg_id, None),message_retry_count.pop(msg_id, None),del_message(bubble_frame)), bg="red", fg="white", width=6, height=1, font=('Arial', 6, 'bold'))
        copybtn.pack(side=LEFT, padx=(0, 5))
        delbtn.pack(side=LEFT, padx=(0, 5))
        btn_frame.pack(pady=5, padx=5, anchor=W)
        date_label = Label(bubble_frame, text=f"{date}", fg='gray', bg=bg_color, anchor=W, justify=LEFT, font=('Arial', 5, 'bold'))
        date_label.pack(pady=(5, 0), padx=5, anchor=W)
        time_label = Label(bubble_frame, text=f"{time}", fg='gray', bg=bg_color, anchor=W, justify=LEFT, font=('Arial', 5, 'bold'))
        time_label.pack(pady=(0,5), padx=5, anchor=W)
        if msg_id is not None:
            status_frame = Frame(bubble_frame, bg=bg_color)
            status_frame.pack(pady=(0, 5), padx=5, anchor=W)
            status_label = Label(status_frame, text="Delivering" if pending else "Delivered",fg='gray', bg=bg_color, font=('Arial', 7, 'italic'))
            status_label.pack(side=LEFT)
            status_bar = None
            if pending:
                status_bar = ttk.Progressbar(status_frame, orient=HORIZONTAL, length=100)
                status_bar.pack(side=LEFT, padx=(8, 0))
                status_bar.start(10)
                pending_messages[msg_id] = {"label": status_label, "bar": status_bar, "frame": status_frame}
        bubble_frame.pack(pady=4, padx=8, anchor=anchor)
        update_scroll()
    elif message_type == "image_message":
        try:
            anchor=W
            bg_color = 'light blue'
            if client_id_num == client_id:
                bg_color = 'light green'
                anchor = E
            else:
                bg_color = 'light blue'
                anchor = W
            image_bytes = b64decode(message)
            raw_img = Image.open(BytesIO(image_bytes))
            raw_img.thumbnail((550, 440))
            tk_img = ImageTk.PhotoImage(raw_img)
            bubble_frame = Frame(tbxmain, bg=bg_color, width=620)
            name_label = Label(bubble_frame, text=f"{name} :", fg='black', bg=bg_color, font=('Arial', 8, 'bold'), anchor=W)
            name_label.pack(pady=(5, 2), padx=5, anchor=W)
            img_label = Label(bubble_frame, image=tk_img, bg=bg_color)
            img_label.image = tk_img
            img_label.pack(pady=2, padx=5, anchor=W)
            if description and description != "none" and description != "":
                desc_label = Label(bubble_frame, text=description, fg='black', bg=bg_color, anchor=W, wraplength=580, justify=LEFT)
                desc_label.pack(pady=(2, 5), padx=5, anchor=W)
            btn_frame = Frame(bubble_frame, bg=bg_color)
            copybtn = Button(btn_frame, text="COPY", command=lambda: copy_to_clipboard(description), bg="green", fg="white", width=6, height=1,font=('Arial', 6, 'bold'))
            saveimagebtn = Button(btn_frame, text="SAVE", command=lambda: save_image(raw_img), bg="green", fg="white", width=6, height=1,font=('Arial', 6, 'bold'))
            delbtn = Button(btn_frame, text="DELETE", command=lambda: (pending_messages.pop(msg_id, None), del_message(bubble_frame)), bg="red", fg="white", width=6, height=1,font=('Arial', 6, 'bold'))
            copybtn.pack(side=LEFT, padx=(0, 5))
            saveimagebtn.pack(side=LEFT, padx=(0, 5))
            delbtn.pack(side=LEFT, padx=(0, 5))
            btn_frame.pack(pady=5, padx=5, anchor=W)
            date_label = Label(bubble_frame, text=f"{date}", fg='gray', bg=bg_color, anchor=W, justify=LEFT, font=('Arial', 5, 'bold'))
            date_label.pack(pady=(5, 0), padx=5, anchor=W)
            time_label = Label(bubble_frame, text=f"{time}", fg='gray', bg=bg_color, anchor=W, justify=LEFT, font=('Arial', 5, 'bold'))
            time_label.pack(pady=(0,5), padx=5, anchor=W)
            if msg_id is not None:
                status_frame = Frame(bubble_frame, bg=bg_color)
                status_frame.pack(pady=(0, 5), padx=5, anchor=W)
                status_label = Label(status_frame, text="Delivering" if pending else "Delivered", fg='gray', bg=bg_color, font=('Arial', 6, 'italic'))
                status_label.pack(side=LEFT)
                status_bar = None
                if pending:
                    status_bar = ttk.Progressbar(status_frame, orient=HORIZONTAL, length=50, mode='indeterminate')
                    status_bar.pack(side=LEFT, padx=(4, 0))
                    status_bar.start(10)
                    pending_messages[msg_id] = {"label": status_label, "bar": status_bar, "frame": status_frame}
            bubble_frame.pack(pady=4, padx=8, anchor=anchor)
            update_scroll()
        except Exception as e:
            print(f"image error: {e}")

def attach_image():
    global image_attached, attached_image
    file_path = filedialog.askopenfilename(
        title="Select Image",
        filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp")]
    )
    if not file_path:
        return
    try:
        raw_img = Image.open(file_path)
        preview_win = Toplevel()
        preview_win.title("Image Preview - μChat")
        preview_win.resizable(False, False)
        preview_win.grab_set()
        thumb_img = raw_img.copy()
        thumb_img.thumbnail((300, 300))
        tk_img = ImageTk.PhotoImage(thumb_img)
        Label(preview_win, text="Do you want to attach this image?", font=("Arial")).pack(pady=5)
        img_label = Label(preview_win, image=tk_img)
        img_label.image = tk_img
        img_label.pack(padx=10, pady=5)
        def confirm():
            global image_attached, attached_image
            with open(file_path, "rb") as image_file:
                attached_image = b64encode(image_file.read()).decode('utf-8')
            image_attached = True
            imagebtn.config(background='green', text='IMAGE')
            preview_win.destroy()
        def cancel():
            preview_win.destroy()
        btn_frame = Label(preview_win)
        btn_frame.pack(fill='x', pady=10)
        Button(btn_frame, text="Confirm", command=confirm, bg="green", fg="white", width=10).pack(side="left", padx=15)
        Button(btn_frame, text="Cancel", command=cancel, bg="red", fg="white", width=10).pack(side="right", padx=15)
    except Exception as e:
        showerror(title='μChat', message=f'Failed to load image preview:\n{e}')

def send(event=None):
    global alreadysending, image_attached, attached_image, uploading_image
    if chat_destroyed:
        return
    try:
        message = ymstbx.get(1.0, 'end-1c').strip()
        if message == '' and not image_attached:
            Thread(target=errorsign).start()
            return
        msg_id = str(uuid4())
        time_str = gettimestamp()
        date_str = getdatestamp()
        if image_attached:
            uploading_image = True
            data = {
                "chat_id": chatID,
                "id_is_visible": id_visible,
                "data": attached_image,
                "message_type": "image_message",
                "name": nickname,
                "description": message if message else "none",
                "time" : time_str,
                "date" : date_str,
                "client_id" : client_id,
                "id": msg_id
            }
            create_new_message_bubble(
                message=attached_image,
                message_type="image_message",
                name=nickname,
                description=message if message else "none",
                time=time_str,
                date=date_str,
                client_id_num=client_id,
                msg_id=msg_id,
                pending=True
            )
            pending_message_data[msg_id] = data
            send_queue.put((msg_id, data))
            attached_image = None
            image_attached = False
            imagebtn.config(background='orange', text='IMAGE')
            ymstbx.delete(1.0, END)
            uploading_image = False
        else:
            data = {
                "chat_id": chatID,
                "id_is_visible": id_visible,
                "data": message,
                "message_type": "text_message",
                "name": nickname,
                "description": "none",
                "time" : time_str,
                "date" : date_str,
                "client_id" : client_id,
                "id": msg_id
            }
            create_new_message_bubble(
                message=message,
                message_type="text_message",
                name=nickname,
                description="none",
                time=time_str,
                date=date_str,
                client_id_num=client_id,
                msg_id=msg_id,
                pending=True
            )
            pending_message_data[msg_id] = data
            send_queue.put((msg_id, data))
            ymstbx.delete(1.0, END)
    except Exception as e:
        showerror(title='μChat', message=f"The server is not responding.\nCan't send message.\n{e}")
    finally:
        alreadysending = False

def destruct_chat():
    def do_destruct():
        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.connect((HOST, PORT_SUB_REQUESTS))
            payload = {
                "request": "destruction",
                "data": dumps({"password": pwd, "room_ID": chatID})
            }
            sock.sendall((dumps(payload) + "\n").encode("utf-8"))
            buffer = ""
            while "\n" not in buffer:
                chunk = sock.recv(4096).decode("utf-8")
                if not chunk:
                    break
                buffer += chunk
            sock.close()
            if buffer.strip():
                result = loads(buffer.strip().split("\n", 1)[0])
                if not result.get("success"):
                    root.after(0, lambda: showerror(title='μChat', message='Destruction failed. Check the password.'))
        except Exception as e:
            root.after(0, lambda: showerror(title='μChat', message=f"Failed to destruct chat.:\n{e}"))
    pwd = password(title='μChat', text='Enter destruction password:')
    if not pwd:
        return
    Thread(target=do_destruct, daemon=True).start()

def handle_room_destruction():
    global chat_destroyed, voice_enabled, audio_enabled
    if chat_destroyed:
        return
    chat_destroyed = True
    clear_chat_frame()
    headertxt.config(text="Room ID : ------- | Ping : -- ms",fg='red')
    voice_enabled = False
    audio_enabled = False
    ymstbx.config(state=DISABLED)
    sbtn.config(state=DISABLED, bg='grey')
    audiobtn.config(state=DISABLED, bg='grey')
    micbtn.config(state=DISABLED, bg='grey')
    imagebtn.config(state=DISABLED, bg='grey')
    destbtn.config(state=DISABLED, bg='grey')
    loadhistbtn.config(state=DISABLED, bg='grey')
    typing_status_label.config(text="", fg='gray')
    mutebtn.config(state=DISABLED, bg='grey')
    pingprogressbar.config(value=0)
    
    try:
        client.close()
    except Exception:
        pass
    try:
        voicesocket.close()
    except Exception:
        pass
    showerror(title='μChat', message='This room has been destructed.\nall messages have been deleted.')
    root.destroy()

def typing_sender(event=None,is_typing=True):
    global chatID, nickname, client_id, typesock
    try:
        if not typesock:
            return
        payload = {
            "request": "typing",
            "data": dumps({
                "room_ID": chatID,
                "name": nickname,
                "typing": is_typing,
                "client_id": client_id
            })
        }
        typesock.sendall((dumps(payload) + "\n").encode("utf-8"))
    except Exception as e:
        pass

def update_typing_label():
    names = list(active_typers.keys())
    if not names:
        typing_status_label.config(text="", fg='gray')
    elif len(names) == 1:
        typing_status_label.config(text=f"{names[0]} is typing...", fg='red')
    else:
        typing_status_label.config(text=", ".join(names) + " are typing...", fg='red')

def remove_typer(name):
    global active_typers
    if name in active_typers:
        active_typers.pop(name, None)
        root.after(0, update_typing_label)

def typing_receiver():
    global typesock
    typesock = socket(AF_INET, SOCK_STREAM)
    typesock.connect((HOST, PORT_SUB_REQUESTS))
    typesock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
    sock = typesock
    if not sock:
        return
    buffer = ""
    while True:
        try:
            chunk = sock.recv(4096).decode("utf-8")
            if not chunk:
                break
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                data = loads(line)
                if data.get("request") != "typing":
                    continue
                room_id = data.get("room_ID")
                name = data.get("name")
                is_typing = data.get("typing")
                sender_client_id = data.get("client_id")
                if room_id == chatID and sender_client_id != client_id:
                    if is_typing:
                        active_typers[name] = True
                        root.after(0, update_typing_label)
                        root.after(1000, lambda n=name: remove_typer(n))
                    else:
                        root.after(0, lambda n=name: remove_typer(n))
        except Exception as e:
            pass

def receive():
    global alreadysending, image_attached,client_id
    buffer = ""
    while True:
        try:
            chunk = client.recv(4096).decode('utf-8')
            if not chunk:
                break
            buffer += chunk
            while "\n" in buffer:
                raw_data, buffer = buffer.split("\n", 1)
                raw_data = raw_data.strip()
                if not raw_data:
                    continue
                data = loads(raw_data)
                
                message_type = data.get("message_type")
                incoming_id = data.get("id")
                
                if message_type in ("room_deleted", "room_destroyed") or data.get("room_destructed"):
                    root.after(0, handle_room_destruction)
                    return
                elif message_type == "error":
                    err_id = data.get("id")
                    if data.get("error") == "message_buffer_too_large":
                        showerror(title='μChat', message=f"Can't send message.\nmessage buffer is too large.")
                    elif data.get("error") == "message_too_large":
                        if err_id:
                            root.after(0, remove_failed_message, err_id)
                    else:
                        showerror(title='μChat', message=f"Can't send message.\n{data.get('error')}")
                    continue

                message = data["data"]
                name = data["name"]
                description = data.get("description", "")
                time = data.get("time", "--:--")
                date = data.get("date", "--/--/----")
                client_id_num = data.get("client_id", "unknown")

                if client_id_num == client_id and incoming_id in pending_messages:
                    root.after(0, mark_message_sent, incoming_id)
                else:
                    root.after(0, lambda m=message, mt=message_type, n=name, d=description, t=time, dt=date, c=client_id_num, i=incoming_id:
                        create_new_message_bubble(message=m, message_type=mt, name=n, description=d, time=t, date=dt, client_id_num=c, msg_id=i, pending=False))

                root.after(0, lambda: (tbxmaincanvas.update_idletasks(), tbxmaincanvas.configure(scrollregion=tbxmaincanvas.bbox("all"))))
                                
                if root.state() != 'normal' and not muted:
                    if message_type == "text_message":
                        root.after(0, lambda: notification_listener(message=message, name=name, message_type=message_type))
                    elif message_type == "image_message":
                        root.after(0, lambda: notification_listener(message=message, name=name, message_type=message_type, description=description))
                if autoscroll.get() == 1:
                    tbxmaincanvas.yview_moveto(1.0)
                
                root.config(bg='green')
                autoscchbx.config(bg='green')
                sticktocorner.config(bg='green')
                headertxt.config(bg='green')
                headertxt.config(fg='black')
                typing_status_label.config(bg='green')
                sleep(0.1)
                root.config(bg='light grey')
                autoscchbx.config(bg='light grey')
                sticktocorner.config(bg='light grey')
                headertxt.config(bg='light grey')
                headertxt.config(fg='green')
                typing_status_label.config(bg='light grey')
                ymstbx.focus()
                alreadysending = False
                image_attached = False
        except Exception as x:
            sleep(0.1)

def load_history():
    try:
        def ignore_btn():
            pass
        promptscreen = Toplevel()
        promptscreen.protocol("WM_DELETE_WINDOW", ignore_btn)
        promptscreen.resizable(False, False)
        promptscreen.title("μChat")
        promptscreen.geometry('300x70')
        toplabel = Label(promptscreen, text="Loading history...", font=("Arial", 12), fg='black')
        toplabel.place(x=10, y=10)
        progressbar = ttk.Progressbar(promptscreen, length=280)
        progressbar.place(x=10, y=40)
        progressbar.config(value=10)
        sock = socket(AF_INET, SOCK_STREAM)
        progressbar.config(value=20)
        sock.connect((HOST, PORT_SUB_REQUESTS))
        progressbar.config(value=30)
        sock.sendall((dumps({"request": "history", "data": dumps({"room_ID": chatID})}) + "\n").encode("utf-8"))
        progressbar.config(value=50)
        buffer = ""
        while True:
            chunk = sock.recv(4096).decode("utf-8")
            if not chunk:
                break
            buffer += chunk
            if "\n" in buffer:
                break
        progressbar.config(value=80)
        data_dict = loads(buffer.strip())
        history = data_dict.get("history", [])
        progressbar.config(value=85)
        clear_chat_frame()
        progressbar.config(value=90)
        for msg in history:
            if msg.get("message_type") == "text_message":
                create_new_message_bubble(message=msg.get("data"), message_type=msg.get("message_type"), name=msg.get("name"), description=msg.get("description"), time=msg.get("time"), date=msg.get("date"), client_id_num=msg.get("client_id"))
            elif msg.get("message_type") == "image_message":
                create_new_message_bubble(name=msg.get("name"), message=msg.get("data"), message_type="image_message", description=msg.get("description"), time=msg.get("time"), date=msg.get("date"),client_id_num=msg.get("client_id"))
        progressbar.config(value=95)
        sock.close()
        progressbar.config(value=100)
        promptscreen.destroy()
        return
    except Exception as e:
        showerror(title='μChat', message=f"Can't load history.\n{e}")
        try :
            promptscreen.destroy()
        except Exception:
            pass
        return
        

def header():
    while True:
        if chat_destroyed:
            break
        s = socket(AF_INET, SOCK_STREAM)
        try:
            st = time()
            s.connect((HOST, PORT_SUB_REQUESTS))
            s.sendall((dumps({"request": "ping", "data": "none"}) + "\n").encode("utf-8"))
            et = time()
            ping = round((et - st) * 1000, 2)
            headertxt.config(fg='green')
        except Exception as x:
            ping = '-1'
            headertxt.config(fg='green')
        headertxt.config(text=f'Room ID : {chatID} | Ping : {ping} ms')
        pingprogressbar.config(value=ping)
        sleep(1)
    
def windowmanager():
    try:
        while True:
            if chat_destroyed:
                break
            if stick.get() == 1:
                root.after(0, lambda: (root.overrideredirect(True), place_top_left(), root.attributes('-topmost', True)))
            else:
                root.after(0, lambda: (root.overrideredirect(False), root.attributes('-topmost', False)))
            sleep(0.2)
    except:
        pass

def mute_chat() :
    global muted
    muted = not muted
    if muted == True:
        mutebtn.config(background='green')
        mutebtn.config(fg='black')
    else:
        mutebtn.config(background='orange')
        mutebtn.config(fg='black')

def place_top_left():
    root.geometry(f"{WIDTH}x{HEIGHT}+0+0")

def enable_audio():
    global audio_enabled, voice_enabled
    audio_enabled = not audio_enabled
    if audio_enabled == True:
        audiobtn.config(background='green')
        audiobtn.config(fg='black')
    else:
        audiobtn.config(background='orange')
        audiobtn.config(fg='black')
        if voice_enabled == True:
            voice_enabled = False
            micbtn.config(background='orange')
            micbtn.config(fg='black')

def enable_mic():
    global voice_enabled, audio_enabled
    voice_enabled = not voice_enabled
    if audio_enabled == False:
        enable_audio()
    if voice_enabled == True and audio_enabled == True:
        micbtn.config(background='green')
        micbtn.config(fg='black')
    else:
        micbtn.config(background='orange')
        micbtn.config(fg='black')

def voice_receiver():
    if not noinputoutput:
        while True:
            if chat_destroyed:
                break
            try:
                data = voicesocket.recv(32768)
                if not data:
                    break
                if audio_enabled == True:
                    output_stream.write(data)
            except Exception as e:
                break

def voice_sender():
    if not noinputoutput:
        global voicesocket
        while True:
            if chat_destroyed:
                break
            try:
                if voice_enabled:
                    data = input_stream.read(CHUNK, exception_on_overflow=False)
                    voicesocket.sendall(data)
                else:
                    sleep(0.1) 
            except Exception as e:
                if chat_destroyed:
                    break
                try:
                    voicesocket.close()
                    voicesocket = socket(AF_INET, SOCK_STREAM)
                    voicesocket.connect((HOST, PORT_VOICE))
                    voicesocket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
                    client.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
                    data = {"chat_id": chatID}
                    voicesocket.sendall(dumps(data).encode("utf-8"))
                except Exception as e:
                    if not chat_destroyed:
                        showerror(title='μChat', message='Voice chat was disconnected.')
                    break

def update_scroll(event=None):
    tbxmaincanvas.configure(scrollregion=tbxmaincanvas.bbox("all"))

def notification_listener(message, name,val=100,message_type="text_message",description=""):
    notification_frame = Frame(background, bg='white', width=315, height=200)
    start_x = -300
    end_x = 50
    notification_frame.place(x=start_x, y=30)
    def slide_in(current_x):
        if current_x < end_x:
            new_x = min(current_x + 10, end_x)
            notification_frame.place(x=new_x, y=30)
            root.after(10, slide_in, new_x)
        else:
            root.after(10, change_progress,val)
    def change_progress(val):  
        try:
            if val != 0:
                val -= 1
                progress_bar.config(value=val)
                root.after(35, change_progress,val)
            else:
                root.after(10, slide_out, end_x)
        except TclError:
            pass
    def slide_out(current_x=end_x):
        if current_x > start_x:
            new_x = max(current_x - 10, start_x)
            notification_frame.place(x=new_x, y=30)
            root.after(10, slide_out, new_x)
        else:
            notification_frame.destroy()
    def open_message():
        root.deiconify()
        root.lift()
        slide_out()
    title_label = Label(notification_frame, text="μChat New Message", fg='black', bg='white', font=('Arial', 11, 'bold'), anchor=W, justify=LEFT)
    name_label = Label(notification_frame, text=name, fg='black', bg='white', font=('Arial', 8, 'bold'), anchor=W, justify=LEFT)
    if message_type == "text_message":
        message_label = Label(notification_frame, text=message[:250], fg='black', bg='white', anchor=W, wraplength=250, justify=LEFT)
    elif message_type == "image_message":
        image_bytes = b64decode(message)
        raw_img = Image.open(BytesIO(image_bytes))
        raw_img.thumbnail((315, 250))
        tk_img = ImageTk.PhotoImage(raw_img)
        message_label = Label(notification_frame,image=tk_img, bg='white', anchor=W, wraplength=250, justify=LEFT,width=250)
        message_label.image=tk_img
        desc_label = Label(notification_frame, text=description if description != "none" else "", fg='black', bg='white', anchor=W, wraplength=250, justify=LEFT)
    progress_bar = ttk.Progressbar(notification_frame, orient=HORIZONTAL, length=315,value=100)
    backbtn = Button(notification_frame, text="X", command=slide_out, bg="red", fg="white", width=4, height=1)
    openbtn = Button(notification_frame, text="^", command=open_message, bg="green", fg="white", width=4, height=1)
    openbtn.place(x=267, y=55)
    backbtn.place(x=267, y=5)
    title_label.pack(pady=5, padx=5, anchor=W)
    name_label.pack(pady=5, padx=5, anchor=W)
    message_label.pack(pady=5, padx=5, anchor=W)
    if message_type == "image_message":
        desc_label.pack(pady=5, padx=5, anchor=W)
    progress_bar.pack(pady=5, padx=5, anchor=W)
    slide_in(start_x)

def sync_frame_width(event):
    tbxmaincanvas.itemconfig(tbxmain_window, width=event.width)

root.bind("<Return>", send)
root.resizable(False, False)
background = Toplevel(root)
background.title('')
background.geometry(f'{root.winfo_width()}x{root.winfo_height()}')
background.config(background='pink')
background.attributes('-fullscreen', True)
background.attributes('-topmost', True)
background.wm_attributes('-transparentcolor', "pink")
autoscroll = IntVar(value=1)
text_variable_stick = IntVar(value=0)
stick = IntVar(value=0)
headertxt = Label(text=f'Room ID : {chatID}', background="light gray", width=68, anchor=W, font=('Arial', 8))
tbxmaincanvas = Canvas(master=root, bg='white', width=618, height=350)
tbxmaincanvas.bind("<Configure>", sync_frame_width)
tbxmaincanvas.place(x=12, y=75)
tbxscrollbar = Scrollbar(master=root, orient=VERTICAL, command=tbxmaincanvas.yview)
tbxmaincanvas.configure(yscrollcommand=tbxscrollbar.set)
tbxscrollbar.place(x=640, y=75, height=353)
tbxmain = Frame(master=tbxmaincanvas, bg='white')
tbxmain_window = tbxmaincanvas.create_window((0, 0), window=tbxmain, anchor='nw')
tbxmain.bind("<Configure>", update_scroll)
autoscchbx = Checkbutton(variable=autoscroll, text='Scroll to bottom', bg='light gray')
sticktocorner = Checkbutton(variable=stick, text='Pin to corner', bg='light gray')
ymstbx = Text(width=49, height=2)
ymstbx.place(x=12, y=435)
sbtn = Button(text='>>', width=5, height=2, background='orange', fg='black', font=('Arial', 8), command=send)
audiobtn = Button(text='LISTEN', width=6, height=1, background='orange', fg='black', font=('Arial', 8), command=enable_audio)
micbtn = Button(text='TALK', width=5, height=1, background='orange', fg='black', font=('Arial', 8), command=enable_mic)
imagebtn = Button(text='IMAGE', width=6, height=1, background='orange', fg='black', font=('Arial', 8), command=attach_image)
destbtn = Button(text='DESTRUCT', width=13, height=1, background='orange', fg='black', font=('Arial', 8), command=destruct_chat)
loadhistbtn = Button(text='LOAD HISTORY', width=15, height=1, background='orange', fg='black', font=('Arial', 8), command=load_history)
mutebtn = Button(text='MUTE', width=5, height=1, background='orange', fg='black', font=('Arial', 8), command=mute_chat)
pingprogressbar = ttk.Progressbar(root, length=200,value=0)
ymstbx.bind("<KeyPress>", typing_sender)
typing_status_label = Label(text='', background="light gray", width=72, anchor=W, font=('Arial', 8, 'italic'), fg='gray')
typing_status_label.place(x=12, y=42)
sbtn.place(x=612, y=435)
autoscchbx.place(x=12, y=485)
sticktocorner.place(x=12, y=512)
headertxt.place(x=12, y=11)
loadhistbtn.place(x=315, y=505)
imagebtn.place(x=468, y=505)
audiobtn.place(x=603, y=505)
micbtn.place(x=540, y=505)
mutebtn.place(x=253, y=505)
destbtn.place(x=540, y=7)
pingprogressbar.place(x=320, y=11)

if noinputoutput:
    audiobtn.config(state=DISABLED, bg='grey')
    micbtn.config(state=DISABLED, bg='grey')
    voice_enabled = False
    audio_enabled = False

Thread(target=receive, daemon=True).start()
Thread(target=header, daemon=True).start()
Thread(target=voice_sender, daemon=True).start()
Thread(target=voice_receiver, daemon=True).start()
Thread(target=typing_receiver, daemon=True).start()
Thread(target=windowmanager, daemon=True).start()
Thread(target=sender_worker, daemon=True).start()

root.mainloop()