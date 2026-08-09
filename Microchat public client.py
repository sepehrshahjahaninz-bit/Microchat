from socket import socket, AF_INET, SOCK_STREAM, IPPROTO_TCP, TCP_NODELAY, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR
from tkinter.messagebox import showerror, showwarning, askyesnocancel, askyesno
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from time import time, sleep, localtime
from pyautogui import password
from threading import Thread
from random import choice
from queue import Queue
from pyaudio import PyAudio, paInt32
from json import loads, dumps
from base64 import b64encode, b64decode
from PIL import Image, ImageTk
from io import BytesIO
from uuid import uuid4
from os import path

WIDTH, HEIGHT = 680, 550
HOST = "chat.shahjahani.com"
PORT_CHAT = 2052
PORT_VOICE = 2082
PORT_PING = 2086
PORT_DELETE = 2053
PORT_MESSAGE_HISTORY = 2054
PORT_TYPING = 2055
CONFIG_FILE = path.join(path.dirname(__file__), "config.json")

connect = 0
nickname = ''
chatID = ''
alreadysending = False
serverfound = False
audio_enabled = False
voice_enabled = False
id_visible = None
connectedormaderoom = None
noinputoutput = False
image_attached = False
attached_image = None
chat_destroyed = False
muted = False
saved_nickname = ""
typing_socket = None
active_typers = {}

root = Tk()
root.withdraw()
root.title('μChat')
root.geometry(f'{WIDTH}x{HEIGHT}')
root.config(background='light gray')
root.resizable(False, False)

try:
    client = socket(AF_INET, SOCK_STREAM)
    client.settimeout(5)
    client.connect((HOST, PORT_CHAT))
    data = loads(client.recv(1024).decode("utf-8"))
    availableclies = data["clients"]
    visiblerooms = data["visible_rooms"]
except Exception as e:
    showerror(title='μChat', message=f'Cannot connect to server.\nErr : {e}')
    quit()

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
        for index, room in enumerate(visiblerooms):
            current_col = index // max_per_column
            current_row = index % max_per_column
            roomslistbox = Frame(inner_frame, bg='white')
            roomlabel = Label(roomslistbox, text=room, font=("Arial", 10),bg="white", fg='black', wraplength=100)
            joinbtn = Button(roomslistbox,command=lambda r=room: validate(r), text="Join", font=("Arial", 8), fg='white', bg='green', width=6)
            roomlabel.pack(side=LEFT, padx=(0, 2))
            joinbtn.pack(side=LEFT)
            roomslistbox.grid(row=current_row, column=current_col, sticky=W, padx=8, pady=2)
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
        def validate(id=None):
            global chatID, nickname, id_visible, connectedormaderoom
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
            if r_id in availableclies:
                chatID = r_id
                nickname = nick
                connectedormaderoom = True
                id_visible = id_visible_var.get()
                save_nickname(nick)
                logindiag.destroy()
            else:
                showerror(title='μChat', message='Invalid Room ID.', parent=logindiag)
        btn_frame = Frame(logindiag)
        btn_frame.pack(fill='x', pady=10)
        Button(btn_frame, text="Join", command=validate, bg="green", fg="white", width=10).pack(side="left", padx=15)
        Button(btn_frame, text="Cancel", command=lambda: (logindiag.destroy(), quit()), bg="red", fg="white", width=10).pack(side="right", padx=15)
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
            chatID = create_an_ID(availableclies)
            nickname = nick
            id_visible = id_visible_var.get()
            connectedormaderoom = False
            save_nickname(nick)
            logindiag.destroy()
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
        "client_id" : client_id
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

def create_new_message_bubble(message, message_type, name, description="",time="--:--", date="--/--/----",client_id_num="unknown"):
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
        delbtn = Button(btn_frame, text="DELETE", command=lambda: del_message(bubble_frame), bg="red", fg="white", width=6, height=1,font=('Arial', 6, 'bold'))
        copybtn.pack(side=LEFT, padx=(0, 5))
        delbtn.pack(side=LEFT, padx=(0, 5))
        btn_frame.pack(pady=5, padx=5, anchor=W)
        date_label = Label(bubble_frame, text=f"{date}", fg='gray', bg=bg_color, anchor=W, justify=LEFT, font=('Arial', 5, 'bold'))
        date_label.pack(pady=(5, 0), padx=5, anchor=W)
        time_label = Label(bubble_frame, text=f"{time}", fg='gray', bg=bg_color, anchor=W, justify=LEFT, font=('Arial', 5, 'bold'))
        time_label.pack(pady=(0,5), padx=5, anchor=W)
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
            delbtn = Button(btn_frame, text="DELETE", command=lambda: del_message(bubble_frame), bg="red", fg="white", width=6, height=1,font=('Arial', 6, 'bold'))
            copybtn.pack(side=LEFT, padx=(0, 5))
            saveimagebtn.pack(side=LEFT, padx=(0, 5))
            delbtn.pack(side=LEFT, padx=(0, 5))
            btn_frame.pack(pady=5, padx=5, anchor=W)
            date_label = Label(bubble_frame, text=f"{date}", fg='gray', bg=bg_color, anchor=W, justify=LEFT, font=('Arial', 5, 'bold'))
            date_label.pack(pady=(5, 0), padx=5, anchor=W)
            time_label = Label(bubble_frame, text=f"{time}", fg='gray', bg=bg_color, anchor=W, justify=LEFT, font=('Arial', 5, 'bold'))
            time_label.pack(pady=(0,5), padx=5, anchor=W)
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
    global alreadysending, image_attached, attached_image
    if chat_destroyed:
        return
    try:
        message = ymstbx.get(1.0, 'end-1c').strip()
        if alreadysending or (message == '' and not image_attached):
            Thread(target=errorsign).start()
            return
        alreadysending = True
        if image_attached:
            data = {
                "chat_id": chatID,
                "id_is_visible": id_visible,
                "data": attached_image,
                "message_type": "image_message",
                "name": nickname,
                "description": message if message else "none",
                "time" : gettimestamp(),
                "date" : getdatestamp(),
                "client_id" : client_id
            }
            client.sendall((dumps(data) + "\n").encode("utf-8"))
            attached_image = None
            image_attached = False
            imagebtn.config(background='orange', text='IMAGE')
            ymstbx.delete(1.0, END)
        else:
            data = {
                "chat_id": chatID,
                "id_is_visible": id_visible,
                "data": message,
                "message_type": "text_message",
                "name": nickname,
                "description": "none",
                "time" : gettimestamp(),
                "date" : getdatestamp(),
                "client_id" : client_id
            }
            client.sendall((dumps(data) + "\n").encode("utf-8"))
            ymstbx.delete(1.0, END)
    except Exception as e:
        showerror(title='μChat', message=f"The server is not responding.\nCan't send message.\n{e}")
    finally:
        alreadysending = False

def destruct_chat():
    pwd = password(title='μChat', text='Enter destruction password:')
    if not pwd:
        return
    try:
        temp_sock = socket(AF_INET, SOCK_STREAM)
        temp_sock.connect((HOST, PORT_DELETE))
        payload = {
            "password": pwd,
            "room_ID": chatID
        }
        temp_sock.sendall(dumps(payload).encode("utf-8"))
        temp_sock.close()
    except Exception as e:
        showerror(title='μChat', message=f"Failed to issue destruction request:\n{e}")

def handle_room_destruction():
    global chat_destroyed, voice_enabled, audio_enabled
    if chat_destroyed:
        return
    chat_destroyed = True
    clear_chat_frame()
    headertxt.config(text="Room was destructed!", fg='red')
    voice_enabled = False
    audio_enabled = False
    ymstbx.config(state=DISABLED)
    sbtn.config(state=DISABLED, bg='grey')
    audiobtn.config(state=DISABLED, bg='grey')
    micbtn.config(state=DISABLED, bg='grey')
    imagebtn.config(state=DISABLED, bg='grey')
    destbtn.config(state=DISABLED, bg='grey')
    loadhistbtn.config(state=DISABLED, bg='grey')
    try:
        client.close()
    except Exception:
        pass
    try:
        voicesocket.close()
    except Exception:
        pass
    showerror(title='μChat', message='This chat has been destructed.')
    root.destroy()

def connect_typing_socket():
    global typing_socket
    try:
        sock = socket(AF_INET, SOCK_STREAM)
        sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        sock.connect((HOST, PORT_TYPING))
        typing_socket = sock
        Thread(target=typing_receiver, daemon=True).start()
    except Exception as e:
        showwarning(title='μChat', message=f'Can\'t connect to typing service.\n{e}')

def typing_sender(event=None,is_typing=True):
    global chatID, nickname, client_id, typing_socket
    try:
        if not typing_socket:
            return
        payload = {
            "room_id": chatID,
            "name": nickname,
            "typing": is_typing,
            "client_id": client_id
        }
        typing_socket.sendall((dumps(payload) + "\n").encode("utf-8"))
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
    global typing_socket, active_typers
    sock = typing_socket
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
                room_id = data.get("room_id")
                name = data.get("name")
                is_typing = data.get("typing")
                sender_client_id = data.get("client_id")
                if room_id == chatID and sender_client_id != client_id:
                    if is_typing:
                        active_typers[name] = True
                        root.after(0, update_typing_label)
                        root.after(1500, lambda n=name: remove_typer(n))
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
                
                if message_type in ("room_deleted", "room_destroyed") or data.get("room_destructed"):
                    root.after(0, handle_room_destruction)
                    return

                message = data["data"]
                name = data["name"]
                description = data.get("description", "")
                time = data.get("time", "--:--")
                date = data.get("date", "--/--/----")
                client_id_num = data.get("client_id", "unknown")
                
                create_new_message_bubble(message=message, message_type=message_type, name=name, description=description, time=time, date=date, client_id_num=client_id_num)
                tbxmaincanvas.update_idletasks()
                tbxmaincanvas.configure(scrollregion=tbxmaincanvas.bbox("all"))
                
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
        sock.connect((HOST, PORT_MESSAGE_HISTORY))
        progressbar.config(value=30)
        sock.sendall((dumps({"room_ID": chatID}) + "\n").encode("utf-8"))
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
            s.connect((HOST, PORT_PING))
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
    if stick.get() == 1:
        root.overrideredirect(True)
        place_top_left()
        root.attributes('-topmost', True)
        root.update_idletasks()
    else:
        root.overrideredirect(False)
        root.attributes('-topmost', False)
        root.update_idletasks()
    root.after(1, windowmanager)

def mute_chat() :
    global muted
    muted = not muted
    if muted == True:
        muutebtn.config(background='green')
        muutebtn.config(fg='black')
    else:
        muutebtn.config(background='orange')
        muutebtn.config(fg='black')

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
def sync_frame_width(event):
    tbxmaincanvas.itemconfig(tbxmain_window, width=event.width)
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
muutebtn = Button(text='MUTE', width=5, height=1, background='orange', fg='black', font=('Arial', 8), command=mute_chat)
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
muutebtn.place(x=253, y=505)
destbtn.place(x=540, y=7)
pingprogressbar.place(x=320, y=11)

if noinputoutput:
    audiobtn.config(state=DISABLED, bg='grey')
    micbtn.config(state=DISABLED, bg='grey')
    voice_enabled = False
    audio_enabled = False

windowmanager()

Thread(target=receive, daemon=True).start()
Thread(target=header, daemon=True).start()
Thread(target=voice_sender, daemon=True).start()
Thread(target=voice_receiver, daemon=True).start()
Thread(target=connect_typing_socket, daemon=True).start()

root.mainloop()