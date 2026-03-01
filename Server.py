import socket, threading

class Server:
    def __init__(self, HOST='127.0.0.1', PORT=5000):
        self.HOST = '127.0.0.1'
        self.PORT = 5000
        isListening: False

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(HOST,PORT)

        self.clientlist = []
        self.userlist = []


    def listening():
        isListening = True
        self.server.listen()

    def public_message(message, _client):
        for client in self.clientlist:
            if client !=_client:
                try:
                    client.send(message)
                except:
                    client.close()
                    client.remove(client)

    def private_message(target, message):
        if target in self.clientlist:
            try:
                self.clientlist[target].send(message)
                return True
            except:
                del clientlist[target]
            return False
    
    def admin_client(client): 
        while True:
            try:
                message = client.recv(1024)
                public_message(message, client)
            except:
                print("client has been disconnected")
                clientlist.remove(client)
                client.close()
                break
    
    def connect_client():
        print(f"running in port {PORT}")
        while True:
            client, adress = self.server.accept()
            print(f"new connection: {adress}")
            clientlist.append(client)

            hilo = threading.Thread(target=admin_client, args=(client,))
            hilo.start