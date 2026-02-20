import socket, threading

HOST = '127.0.0.1'
PORT = 5000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

clientes = []
usuarios = []

def mensaje_publico(mensaje, _cliente):
    for cliente in clientes:
        if cliente != _cliente:
            try:
                cliente.send(mensaje)
            except:
                cliente.close()
                cliente.remove(cliente)

def mensaje_privado(usuario_destino, mensaje):
    if usuario_destino in clientes:
        try:
            clientes[usuario_destino].send(mensaje)
            return True
        except:
            del clientes[usuario_destino]
    return False

def gestion_cliente(cliente): #despacha un hilo por cada cliente conectado
    while True:
        try:
            mensaje = cliente.recv(1024)
            mensaje_publico(mensaje, cliente)
        except:
            print("cliente desconectado")
            clientes.remove(cliente)
            cliente.close()
            break

def conectar_cliente():
    print(f"el servidor esta corriendo en el puerto {PORT}")
    while True:
        cliente, direccion = server.accept()
        print(f"Nueva conexion: {direccion}")
        clientes.append(cliente)

        hilo = threading.Thread(target=gestion_cliente, args=(cliente,))
        hilo.start

conectar_cliente()