import socket
import json
import argparse

def build_request(path):
    
    return f"GET {path}\n"


def send_request(host, port, request_str):
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    f = None
    
    try:
        try:
            s.connect((host, port))
        except Exception as e:
            
            response = {
                "status": "CLIENT_CONNECTION_ERROR",
                "data": None
            }
            
            res = json.dumps(response) + '\n'
            return res
        
        f = s.makefile('r', encoding = 'utf-8', newline = '\n')
        s.sendall(request_str.encode('utf-8'))
        
        first_line = f.readline()
        
        if first_line: 
            return json.loads(first_line)
        else:
            response = {
                "status": "CLIENT_CONNECTION_ERROR",
                "data": None
            }
            res = json.dumps(response) + '\n'
            return res
    finally:
        if f:
            f.close()
        s.close()
            
def run(args):
    
    url = args.get
    request_str = build_request(url)
    print(send_request(args.host, args.port, request_str))
    
    
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        "--host",
        type = str,
        default = "127.0.0.1"
    )   
    
    parser.add_argument(
        "--port",
        type = int,
        required = True
    )
    
    parser.add_argument(
        "--get",
        type = str,
        required = True
    )
    
    args = parser.parse_args()
    run(args)