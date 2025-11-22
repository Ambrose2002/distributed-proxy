import socket
import json
import time
from datetime import datetime

HOST = "127.0.0.1"
PORT = 8000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(5)

    while True:

        conn, add = s.accept()

        with conn: 
            print(f"Connected by: {add} at {datetime.now()}")
            data = conn.recv(1024)
            if not data:
                continue
            data = data.decode('utf-8').strip()
            method, url = data.split(" ")
            
            if method != "GET":
                res = {
                    "status": "WRONG_METHOD",
                    "data": f"{method} is not currently supported"
                }
                res_string = json.dumps(res) + "\n"
                time.sleep(0.1)
                conn.sendall(res_string.encode('utf-8'))
                
                continue
                
            resource, key = url.split("/", 1)
            filepath = "data/" + resource + key + ".json"
            print(f"{method} to file at {filepath}")
            try: 
                with open(filepath) as f:
                    fetched_data = json.load(f)
                res = {
                    "status": "OK",
                    "data": fetched_data
                }
                res_string = json.dumps(res) + "\n"
                time.sleep(0.1)
                conn.sendall(res_string.encode('utf-8'))
            except Exception as e:
                res = {
                    "status": "NOT_FOUND",
                    "data": f"An error occured: {e}"
                }
                print(f"There was an error: {e}" )
                res_string = json.dumps(res) + "\n"
                time.sleep(0.1)
                conn.sendall(res_string.encode('utf-8'))
        
        