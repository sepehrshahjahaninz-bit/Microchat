from socket import socket, AF_INET, SOCK_STREAM, IPPROTO_TCP, TCP_NODELAY
from tkinter.messagebox import showerror, showwarning, askyesnocancel, showinfo
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from time import time, sleep
from pyautogui import prompt
from plyer import notification
from threading import Thread
from random import choice
from queue import Queue
from pyaudio import PyAudio, paInt32
from json import loads, dumps
import base64
from PIL import Image, ImageTk
import io

WIDTH, HEIGHT = 460, 520
HOST = "chat.shahjahani.com"
PORT_CHAT = 2052
PORT_VOICE = 2082
PORT_PING = 2086
PORT_DELETE = 2053

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

def create_a_name(availableclies):
    data = [0,1,2,3,4,5,6,7,8,9]
    nickname = str(choice(data))
    for i in range(6):
        nickname = nickname + str(choice(data))
    while nickname in availableclies:
        nickname = create_a_name(availableclies)
        return
    return nickname

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

while chatID == '':
    a = askyesnocancel(title='μChat', message='Do you want to join a chat? Click no if you would like to create a new room.')
    if a == True:
        CID = prompt(title='μChat', text=f'Enter Room ID\nAvailable rooms : {visiblerooms}')
        if CID is None:
            quit()
        else:
            try:
                if CID in availableclies:
                    chatID = CID
                    connectedormaderoom = True
                    break
                else:
                    showerror(title='μChat', message='Invalid Room ID.')
            except:
                showerror(title='μChat', message='Invalid Room ID.')
    elif a == False:
        CID = str(create_a_name(availableclies))
        connectedormaderoom = False
        chatID = CID
    elif a == None:
        quit()

while id_visible == None and connectedormaderoom == False:
    result = askyesnocancel(title='μChat', message='Make room visible to people connecting?')
    if result == True:
        id_visible = True
        break
    elif result == False:
        id_visible = False
        break
    elif result == None:
        quit()

while nickname == '':
    nickname = prompt(title='μChat', text='Enter your nickname')
    if nickname is None:
        quit()
    elif nickname == '':
        showwarning(title='μChat', message='Nickname required.')

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
        bubble_frame = Frame(tbxmain, bg='light green', width=390)
        name_label = Label(bubble_frame, text=name, fg='black', bg='light green', font=('Arial', 8, 'bold'), anchor=W, justify=LEFT)
        name_label.pack(pady=(5, 0), padx=5, anchor=W)
        message_label = Label(bubble_frame, text=text, fg='black', bg='light green', anchor=W, wraplength=250, justify=LEFT)
        message_label.pack(pady=5, padx=5, anchor=W)
        bubble_frame.pack(pady=4, padx=8, anchor=W)
        update_scroll()
    elif message_type == "image_message":
        try:
            image_bytes = base64.b64decode(message)
            raw_img = Image.open(io.BytesIO(image_bytes))
            raw_img.thumbnail((220, 220))
            tk_img = ImageTk.PhotoImage(raw_img)
            bubble_frame = Frame(tbxmain, bg='light green', width=390)
            name_label = Label(bubble_frame, text=f"{name} :", fg='black', bg='light green', font=('Arial', 8, 'bold'), anchor=W)
            name_label.pack(pady=(5, 2), padx=5, anchor=W)
            img_label = Label(bubble_frame, image=tk_img, bg='light green')
            img_label.image = tk_img
            img_label.pack(pady=2, padx=5, anchor=W)
            if description and description != "none":
                desc_label = Label(bubble_frame, text=description, fg='black', bg='light green', anchor=W, wraplength=220, justify=LEFT)
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
                        notification.notify(
                            title="New Message",
                            message=f'{name}: {message}',
                            app_name="μChat",
                            timeout=5
                        )
                    elif message_type == "image_message":
                        notification.notify(
                            title="New Message",
                            message=f'Image from {name}:\n{description}',
                            app_name="μChat",
                            timeout=5
                        )
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

root = Tk()
root.title('μChat')
root.geometry(f'{WIDTH}x{HEIGHT}')
root.config(background='light gray')
root.bind("<Return>", send)
root.resizable(False, False)
autoscroll = IntVar(value=1)
text_variable_stick = IntVar(value=0)
stick = IntVar(value=0)
headertxt = Label(text=f'Room ID : {chatID}', background="light gray", width=47, anchor=W, font=('Arial', 8))
tbxmaincanvas = Canvas(master=root, bg='white', width=390, height=352)
tbxmaincanvas.place(x=12, y=50)
tbxscrollbar = Scrollbar(master=root, orient=VERTICAL, command=tbxmaincanvas.yview)
tbxmaincanvas.configure(yscrollcommand=tbxscrollbar.set)
tbxscrollbar.place(x=410, y=50, height=355)
tbxmain = Frame(master=tbxmaincanvas, bg='white')
tbxmain_window = tbxmaincanvas.create_window((0, 0), window=tbxmain, anchor='nw')
tbxmain.bind("<Configure>", update_scroll)
autoscchbx = Checkbutton(variable=autoscroll, text='Scroll to bottom', bg='light gray')
sticktocorner = Checkbutton(variable=stick, text='Pin to corner', bg='light gray')
ymstbx = Text(width=30, height=1)
ymstbx.place(x=10, y=420)
sbtn = Button(text='>>', width=4, height=1, background='orange', fg='black', font=('Arial', 8), command=send)
audiobtn = Button(text='LISTEN', width=7, height=1, background='orange', fg='black', font=('Arial', 8), command=enable_audio)
micbtn = Button(text='TALK', width=5, height=1, background='orange', fg='black', font=('Arial', 8), command=enable_mic)
imagebtn = Button(text='IMAGE', width=6, height=1, background='orange', fg='black', font=('Arial', 8), command=attach_image)
destbtn = Button(text='DESTRUCT', width=12, height=1, background='orange', fg='black', font=('Arial', 8), command=destruct_chat)
sbtn.place(x=390, y=418)
autoscchbx.place(x=10, y=450)
sticktocorner.place(x=10, y=480)
headertxt.place(x=12, y=11)
audiobtn.place(x=300, y=465)
micbtn.place(x=380, y=465)
imagebtn.place(x=230, y=465)
destbtn.place(x=320, y=11)

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