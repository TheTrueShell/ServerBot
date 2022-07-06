import contextlib
from server import getServerList
import mcstatus
import socket
from configparser import ConfigParser
import json
from datetime import datetime

parser = ConfigParser()
parser.read("config.ini")

sshIP = parser.get("SSH", "IP")
sshLOCATION = (sshIP, 22)


def check_ping():
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result_of_check = a_socket.connect_ex(sshLOCATION)
    a_socket.close()
    return result_of_check == 0


servers = getServerList()


def update_status():
    onlineServers = []
    onlinePlayers = 0
    if check_ping():
        for server in servers:
            online = False
            with contextlib.suppress(Exception):
                MCServer = mcstatus.MinecraftServer.lookup(server.address)
                status = MCServer.query()
                online = True
            if online:
                print(f"{server.name}: Online")
                onlineServers.append(server.name)
                onlinePlayers += status.players.online
    dictionary = {
        "onlineServers": onlineServers,
        "onlinePlayers": onlinePlayers,
    }
    currentDateTime = datetime.now()
    dt_string = currentDateTime.strftime("%d/%m/%Y %H:%M:%S")
    print(f"[{dt_string}] - {dictionary}")
    with open("server_statuses.json", "w") as file:
        json.dump(dictionary, file)

if __name__ == "__main__":
    update_status()