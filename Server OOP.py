import socket
class Client:
    
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host =  "127.0.0.1"
        self.port = 5000
        self.bind = self.server.bind((self.host, self.port))
    
    def listen():
        #self.server.listen()
        pass

    def public_message():
        pass

    def private_message():
        pass

    def client_administration():
        pass

    def connect_client():
        pass




    

