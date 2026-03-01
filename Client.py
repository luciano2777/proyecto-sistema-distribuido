import socket, threading

class Cliente:
    def __init__(self, HOST='127.0.0.1', PORT=5000 ):
        self.HOST = '127.0.0.1'
        self.PORT = 5000
        self.username = self.username
        self.cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.isRunning = False

    def Connect(): #FIXME
        self.cliente.connect((self.HOST, self.PORT))
        isRunning = True

    def Disconnect():
        self.cliente.close()
        print("The Client has Disconnected")
        isRunning = False
        pass

    def sendMessage():
        while True:
            Message = input()
            self.cliente.send(Message.encode("utf-8"))

    def recieveMessage():
        while True:
            try:
                Message = self.cliente.recv(1024).decode("utf-8")
                print("\n" + Message)
            except:
                print("Dissconnected from Server")
                self.Disconnect()
    


# HILOS
    recieve_thread = threading.Thread(target=recieveMessage)
    recieve_thread.start()

    send_thread = threading.Thread(target=sendMessage)
    send_thread.start()







    

