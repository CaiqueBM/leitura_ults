import socket

def enviar_mensagem(numero, mensagem):
    HOST =  '127.0.0.1'  # O endereço IP do servidor JavaScript
    PORT = 65432        # A porta em que o servidor JavaScript está ouvindo

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(f"{numero}${mensagem}\n".encode())