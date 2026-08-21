# Microchat
A simple lightweight messaging app that works over LAN and can be self hosted on a server with a public IP.
it works by clients connecting to the server and either joining a room or creating a new one.
Microchat has features including :
- Voice chat (Experimental)
- Sending images
- Room destruction (Permanently removes the room and its messages and everyone disconnects. Note : The room's message log is still stored on the server,
  but it is flagged as destructed in the room's log file so it is not visible to clients.
- Custom designed toast notifications.
