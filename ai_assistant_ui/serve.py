from textual_serve.server import Server

if __name__ == "__main__":
    server = Server("../.venv/bin/python main.py")
    server.serve()