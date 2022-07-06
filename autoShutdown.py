import contextlib
import server
import mcstatus
from time import sleep
import os
import sys
from datetime import datetime
servers = server.getServerList()
from configparser import ConfigParser

def testing(parser):
    return parser.get("AutoShutdown", "testing") == "1"


def serverOnline(currentServer):
    online = False
    with contextlib.suppress(BaseException):
        ms = mcstatus.MinecraftServer.lookup(currentServer.address)
        ms.ping()
        online = True
    return online


def serverStatus(currentServer):
    try:
        ms = mcstatus.MinecraftServer.lookup(currentServer.address)
        msStatus = ms.query()
    except BaseException:
        msStatus = None
    return msStatus


def stopServer(currentServer):
    # recordCheatUsage(currentServer)
    sessionName = "{0}Server".format(currentServer.location)
    os.system("tmux send-keys -t {0} 'stop' Enter".format(sessionName))
    sleep(60)
    os.system("tmux send-keys -t {0} 'exit' Enter".format(sessionName))
    sleep(1)
    os.system("tmux send-keys -t {0} 'exit' Enter".format(sessionName))
    sleep(1)
    online = serverOnline(currentServer)
    return not online


def auto_shutdown(parser):
    emptyServers = []
    for server in servers:
        if online := serverOnline(server):
            currentDateTime = datetime.now()
            dt_string = currentDateTime.strftime("%d/%m/%Y %H:%M:%S")
            status = serverStatus(server)
            if status.players.online == 0:
                print("{0} - {1}: Online & Empty".format(dt_string, server.name))
                emptyServers.append(server)
            else:
                print("{0} - {1}: Online & Populated".format(dt_string, server.name))
    currentDateTime = datetime.now()
    dt_string = currentDateTime.strftime("%d/%m/%Y %H:%M:%S")
    if emptyServers:
        print(f"{dt_string} - Waiting 5 minutes...")
        sleep(300)
        for server in emptyServers:
            if online := serverOnline(server):
                status = serverStatus(server)
                if status.players.online == 0:
                    currentDateTime = datetime.now()
                    dt_string = currentDateTime.strftime("%d/%m/%Y %H:%M:%S")
                    print(
                        "{0} - Sent shutdown commands to {1}".format(dt_string, server.name))
                    success = stopServer(server)
                    checkTmux(server)
                    currentDateTime = datetime.now()
                    dt_string = currentDateTime.strftime("%d/%m/%Y %H:%M:%S")
                    if success:
                        print(
                            "{0} - Successfully shutdown {1} Server".format(dt_string,
                                                                            server.name))
                    else:
                        print(
                            "{0} - Failed to shutdown {1} Server".format(dt_string,
                                                                         server.name))
        doFullShutdown = parser.get("AutoShutdown", "doFullShutdown")
        if doFullShutdown == "1":
            onlineServers = []
            for server in servers:
                if online := serverOnline(server):
                    onlineServers.append(server)
            if not onlineServers:
                sshUSER = parser.get("SSH", "user")
                sshPASS = parser.get("SSH", "pass")
                sshIP = parser.get("SSH", "IP")
                currentDateTime = datetime.now()
                dt_string = currentDateTime.strftime("%d/%m/%Y %H:%M:%S")
                print("{0} - Sent shutdown commands to {1}".format(dt_string, server.name))
                print("Fully Shutting Down PC...")
                sessionName = "shutdownSession"
                os.system("tmux new -s {0} -d".format(sessionName))
                sleep(1)
                os.system(
                    "tmux send-keys -t {0} 'ssh {1}@{2}' Enter".format(sessionName, sshUSER, sshIP))
                sleep(1)
                os.system(
                    "tmux send-keys -t {0} '{1}' Enter".format(sessionName, sshPASS))
                sleep(1)
                os.system(
                    "tmux send-keys -t {0} 'shutdown /s' Enter".format(sessionName))
                sleep(1)
                os.system("tmux send-keys -t {0} 'exit' Enter".format(sessionName))
                sleep(1)
                os.system("tmux send-keys -t {0} 'exit' Enter".format(sessionName))
                sleep(1)
    else:
        print(f"{dt_string} - No Empty Servers... Skipping...")          

def checkTmux(server):
    out = os.popen("tmux ls")
    if server.location in out and not serverOnline(server):
        sleep(30)
        if not serverOnline(server):
            os.system(f"tmux kill -t {server.location}")

path = os.path.dirname(sys.argv[0])

parserMain = ConfigParser()
parserMain.read("config.ini".format(path))
if testing(parserMain):
    print(parserMain.sections())

auto_shutdown(parserMain)
print("----")
