import socket
import json
import time

HOST = "127.0.0.1"
PORT = 8000

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(5)

while True:

    conn, add = s.accept()

    with conn: 
        print("Connected by: ", add)
        data = conn.recv(1024)
        if not data:
            break
        data = data.decode('utf-8').strip()
        method, url = data.split(" ")
        resource, key = url.split("/", 1)
        filepath = "data/" + resource + key + ".json"
        
        try: 
            with open(filepath) as f:
                fetched_data = json.loads(f.read())
            res = {
                "status": "OK",
                "data": fetched_data
            }
            res_string = json.dumps(res)
            time.sleep(0.1)
            conn.sendall(res_string.encode('utf-8'))
        except Exception as e:
            res = {
                "status": "NOT_FOUND",
                "data": "An error occured: {e}"
            }
            res_string = json.dumps(res)
            time.sleep(0.1)
            conn.sendall(res_string.encode('utf-8'))
        
        