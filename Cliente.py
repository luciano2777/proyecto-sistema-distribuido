import socket
import threading

HOST = '127.0.0.1'
PORT = 5000

cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
cliente.connect((HOST, PORT))

def recibir_mensaje():
    while True:
        try:
            mensaje = cliente.recv(1024).decode("utf-8")
            print("\n" + mensaje)
        except:
            print("Desconectado del servidor")
            cliente.close()
            break

def enviar_mensaje():
    while True:
        mensaje = input()
        cliente.send(mensaje.encode("utf-8"))

hilo_recibir = threading.Thread(target=recibir_mensaje)
hilo_recibir.start()

hilo_enviar = threading.Thread(target=enviar_mensaje)
hilo_enviar.start()