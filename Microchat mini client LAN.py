from socket import socket, AF_INET, SOCK_STREAM, IPPROTO_TCP, TCP_NODELAY, SOCK_DGRAM
from tkinter.messagebox import showerror, showwarning, askyesnocancel, showinfo
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from time import time, sleep
from pyautogui import prompt
from threading import Thread
from random import choice
from queue import Queue
from pyaudio import PyAudio, paInt32
from json import loads, dumps
import base64
from PIL import Image, ImageTk
import io

WIDTH, HEIGHT = 680, 520
PORT_CHAT = 2052
PORT_VOICE = 2082
PORT_PING = 2086
PORT_DELETE = 2053
PORT_MESSAGE_HISTORY = 2054
PORT_FINDER = 4488
HOST = None

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
connection_attempts = 0

def create_a_name(availableclies):
    data = [0,1,2,3,4,5,6,7,8,9]
    nickname = str(choice(data))
    for i in range(6):
        nickname = nickname + str(choice(data))
    while nickname in availableclies:
        nickname = create_a_name(availableclies)
        return
    return nickname

root = Tk()
root.withdraw()
root.title('μChat')
root.geometry(f'{WIDTH}x{HEIGHT}')
root.config(background='light gray')
root.resizable(False, False)

try :
    finder = socket(AF_INET,SOCK_DGRAM)
    finder.settimeout(0.1)
except Exception as e:
    showerror(title='μChat', message=f'Cannot Search for Server.\nErr : {e}')
    quit()

try :
    while serverfound == False and connection_attempts < 25 :
        try :
            finder.sendto(b'//*LOOKING FOR SERVER//*',('239.255.255.250',PORT_FINDER))
            data, addr = finder.recvfrom(1024)
            if data == b'//*SERVER IS HERE//*' :  
                HOST = addr[0]
                serverfound = True
                break
        except Exception as x:
            sleep(0.2)
    else :
        if serverfound == False :
            showerror(title='μChat', message='Server not found or broadcast packets are blocked.')
            quit()
except Exception as e:
    showerror(title='μChat', message=f'Cannot find any listening server.\nErr : {e}')
    quit()

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

def show_login_dialog():
    global chatID, nickname, id_visible, connectedormaderoom
    a = askyesnocancel(title='μChat', message='Do you want to join a chat? Click No to create a new room.')
    if a is None:
        quit()
    logindiag = Toplevel(root)
    logindiag.title('μChat')
    logindiag.geometry('460x250')
    logindiag.resizable(False, False)
    if a is True:
        toplabel = Label(logindiag, text="Enter the room ID to join.", font=("Arial", 10), fg='black')
        toplabel.pack(anchor=W, padx=10, pady=(5, 0))
        publicrooms = Label(logindiag, text=f"Available rooms: {visiblerooms}", font=("Arial", 9), fg='black',wraplength=400)
        publicrooms.pack(anchor=W, padx=10)
        Label(logindiag, text="Room ID:").pack(anchor=W, padx=10)
        idfield = Entry(logindiag, width=50)
        idfield.pack(anchor=W, padx=10)
        idfield.focus()
        Label(logindiag, text="Nickname:").pack(anchor=W, padx=10)
        nicknamefield = Entry(logindiag, width=50)
        nicknamefield.pack(anchor=W, padx=10)
        id_visible_var = BooleanVar(value=True)
        def validate():
            global chatID, nickname, id_visible, connectedormaderoom
            r_id = idfield.get().strip()
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
        nicknamefield.focus()
        id_visible_var = BooleanVar(value=True)
        Checkbutton(logindiag, text="Room visible publicly", variable=id_visible_var).pack(anchor=W, padx=10, pady=5)
        def create_room():
            global chatID, nickname, id_visible, connectedormaderoom
            nick = nicknamefield.get().strip()
            if not nick:
                showerror(title='μChat', message='Nickname cannot be empty.', parent=logindiag)
                return
            chatID = create_a_name(availableclies)
            nickname = nick
            id_visible = id_visible_var.get()
            connectedormaderoom = False
            logindiag.destroy()
        btn_frame = Frame(logindiag)
        btn_frame.pack(fill='x', pady=10)
        Button(btn_frame, text="Create", command=create_room, bg="green", fg="white", width=10).pack(side="left", padx=15)
        Button(btn_frame, text="Cancel", command=lambda: (logindiag.destroy(), quit()), bg="red", fg="white", width=10).pack(side="right", padx=15)
    root.wait_window(logindiag)

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

def create_new_message_bubble(message, message_type, name, description=""):
    if message_type == "text_message":
        text = f"{message}"
        bubble_frame = Frame(tbxmain, bg='light green', width=620)
        name_label = Label(bubble_frame, text=name, fg='black', bg='light green', font=('Arial', 8, 'bold'), anchor=W, justify=LEFT)
        name_label.pack(pady=(5, 0), padx=5, anchor=W)
        message_label = Label(bubble_frame, text=text, fg='black', bg='light green', anchor=W, wraplength=580, justify=LEFT)
        message_label.pack(pady=5, padx=5, anchor=W)
        bubble_frame.pack(pady=4, padx=8, anchor=W)
        update_scroll()
    elif message_type == "image_message":
        try:
            image_bytes = base64.b64decode(message)
            raw_img = Image.open(io.BytesIO(image_bytes))
            raw_img.thumbnail((550, 440))
            tk_img = ImageTk.PhotoImage(raw_img)
            bubble_frame = Frame(tbxmain, bg='light green', width=620)
            name_label = Label(bubble_frame, text=f"{name} :", fg='black', bg='light green', font=('Arial', 8, 'bold'), anchor=W)
            name_label.pack(pady=(5, 2), padx=5, anchor=W)
            img_label = Label(bubble_frame, image=tk_img, bg='light green')
            img_label.image = tk_img
            img_label.pack(pady=2, padx=5, anchor=W)
            if description and description != "none":
                desc_label = Label(bubble_frame, text=description, fg='black', bg='light green', anchor=W, wraplength=580, justify=LEFT)
                desc_label.pack(pady=(2, 5), padx=5, anchor=W)
            bubble_frame.pack(pady=4, padx=8, anchor=W)
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
                attached_image = base64.b64encode(image_file.read()).decode('utf-8')
            image_attached = True
            imagebtn.config(background='green', text='IMAGE')
            preview_win.destroy()
        def cancel():
            preview_win.destroy()
        btn_frame = Label(preview_win)
        btn_frame.pack(fill='x', pady=10)
        Button(btn_frame, text="Confirm", command=confirm, bg="#4CAF50", fg="white", width=10).pack(side="left", padx=15)
        Button(btn_frame, text="Cancel", command=cancel, bg="#f44336", fg="white", width=10).pack(side="right", padx=15)
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
            }
            client.sendall((dumps(data) + "\n").encode("utf-8"))
            ymstbx.delete(1.0, END)
    except Exception as e:
        showerror(title='μChat', message=f"The server is not responding.\nCan't send message.\n{e}")
    finally:
        alreadysending = False

def destruct_chat():
    pwd = prompt(title='μChat', text='Enter destruction password:')
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

def receive():
    global alreadysending, image_attached
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
                description = data.get("description", "none")
                
                create_new_message_bubble(message, message_type, name, description)
                tbxmaincanvas.update_idletasks()
                tbxmaincanvas.configure(scrollregion=tbxmaincanvas.bbox("all"))
                
                if root.state() != 'normal':
                    if message_type == "text_message":
                        root.after(0, notification_listener, message, name)
                    elif message_type == "image_message":
                        root.after(0, notification_listener, f'Image from {name}:\n{description}', name)
                if autoscroll.get() == 1:
                    tbxmaincanvas.yview_moveto(1.0)
                root.config(bg='green')
                autoscchbx.config(bg='green')
                sticktocorner.config(bg='green')
                headertxt.config(bg='green')
                headertxt.config(fg='black')
                sleep(0.1)
                root.config(bg='light grey')
                autoscchbx.config(bg='light grey')
                sticktocorner.config(bg='light grey')
                headertxt.config(bg='light grey')
                headertxt.config(fg='green')
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
                create_new_message_bubble(msg.get("data"), msg.get("message_type"), msg.get("name"), msg.get("description"))
            elif msg.get("message_type") == "image_message":
                create_new_message_bubble(name=msg.get("name"), message=msg.get("data"), message_type="image_message", description=msg.get("description"))
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

def notification_listener(message, name):
    global val
    notification_frame = Frame(background, bg='white', width=300, height=200)
    start_x = -300
    end_x = 50
    val=100
    notification_frame.place(x=start_x, y=30)
    def slide_in(current_x):
        if current_x < end_x:
            new_x = min(current_x + 10, end_x)
            notification_frame.place(x=new_x, y=30)
            root.after(10, slide_in, new_x)
        else:
            root.after(10, change_progress)
    def change_progress():  
        global val
        try:
            if val != 0:
                val -= 1
                progress_bar.config(value=val)
                root.after(35, change_progress)
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
    title_label = Label(notification_frame, text="μChat New Message", fg='black', bg='white', font=('Arial', 11, 'bold'), anchor=W, justify=LEFT)
    name_label = Label(notification_frame, text=name, fg='black', bg='white', font=('Arial', 8, 'bold'), anchor=W, justify=LEFT)
    message_label = Label(notification_frame, text=message[:250], fg='black', bg='white', anchor=W, wraplength=250, justify=LEFT)
    progress_bar = ttk.Progressbar(notification_frame, orient=HORIZONTAL, length=300,value=100)
    backbtn = Button(notification_frame, text="X", command=slide_out, bg="red", fg="white", width=4, height=1)
    backbtn.place(x=250, y=10)
    title_label.pack(pady=5, padx=5, anchor=W)
    name_label.pack(pady=5, padx=5, anchor=W)
    message_label.pack(pady=5, padx=5, anchor=W)
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
tbxmaincanvas.place(x=12, y=45)
tbxscrollbar = Scrollbar(master=root, orient=VERTICAL, command=tbxmaincanvas.yview)
tbxmaincanvas.configure(yscrollcommand=tbxscrollbar.set)
tbxscrollbar.place(x=640, y=45, height=353)
tbxmain = Frame(master=tbxmaincanvas, bg='white')
tbxmain_window = tbxmaincanvas.create_window((0, 0), window=tbxmain, anchor='nw')
tbxmain.bind("<Configure>", update_scroll)
autoscchbx = Checkbutton(variable=autoscroll, text='Scroll to bottom', bg='light gray')
sticktocorner = Checkbutton(variable=stick, text='Pin to corner', bg='light gray')
ymstbx = Text(width=49, height=2)
ymstbx.place(x=12, y=405)
sbtn = Button(text='>>', width=5, height=2, background='orange', fg='black', font=('Arial', 8), command=send)
audiobtn = Button(text='LISTEN', width=6, height=1, background='orange', fg='black', font=('Arial', 8), command=enable_audio)
micbtn = Button(text='TALK', width=5, height=1, background='orange', fg='black', font=('Arial', 8), command=enable_mic)
imagebtn = Button(text='IMAGE', width=6, height=1, background='orange', fg='black', font=('Arial', 8), command=attach_image)
destbtn = Button(text='DESTRUCT', width=13, height=1, background='orange', fg='black', font=('Arial', 8), command=destruct_chat)
loadhistbtn = Button(text='LOAD HISTORY', width=15, height=1, background='orange', fg='black', font=('Arial', 8), command=load_history)
sbtn.place(x=612, y=405)
autoscchbx.place(x=12, y=455)
sticktocorner.place(x=12, y=482)
headertxt.place(x=12, y=11)
loadhistbtn.place(x=315, y=465)
imagebtn.place(x=468, y=465)
audiobtn.place(x=603, y=465)
micbtn.place(x=540, y=465)
destbtn.place(x=540, y=7)

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

root.mainloop()