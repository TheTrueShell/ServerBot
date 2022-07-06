 # Deps
# External Imports
import server
import socket
import sys
import mcstatus
import discord
from discord.ext import commands
from discord.ext import tasks
import os
import asyncio
from datetime import datetime
from configparser import ConfigParser
import json


# Internal Imports

# TODO
# Test test test

parser = ConfigParser()
parser.read("config.ini")

bot_name = parser.get("Bot", "name")

# Import Token
TOKEN = parser.get("Bot", "token")

bot = commands.Bot(command_prefix="!!")
bot.owner_id = parser.get("Bot", "owner_id")

loadingIcon = "<a:loadingbuffering:879522510935306300>"

# Importing servers. Add in server.py class file
servers = server.getServerList()

# SSH
sshIP = parser.get("SSH", "IP")
sshUSER = parser.get("SSH", "user")
sshPASS = parser.get("SSH", "pass")
sshLOCATION = (sshIP, 22)

# Args
defaultDrive = parser.get("SSH", "drive")
defaultLocation = parser.get("SSH", "location")


# Display on bot login
@bot.event
async def on_ready():
    print('Logged in as {0.user} in {1} different guilds.'.format(
        bot, str(len(bot.guilds))))


# Functions
async def check_ping():
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result_of_check = a_socket.connect_ex(sshLOCATION)
    a_socket.close()
    return result_of_check == 0


# Wakes PC
async def wakePC():
    mac = parser.get("SSH", "mac")
    os.system(f"sudo etherwake -i eth0 {mac}")


# Pings User
async def pingUser(ctx):
    user = ctx.message.author.mention
    message = await ctx.send("{}: You have a notification.".format(user))
    await message.delete()


# Print time
async def logging(ctx, command):
    currentDateTime = datetime.now()
    dt_string = currentDateTime.strftime("%d/%m/%Y %H:%M:%S")
    print("[{0}] - {1} executed the {2} command.".format(dt_string,
          ctx.message.author, command))


# Starts HW server
async def startServer(ctx, botmessage, currentServer):
    # Define Embeds
    serverTitle = "{0}: Server Manager".format(
        f'{currentServer.emojiStr} {currentServer.name}'
    )

    online = await serverOnline(currentServer)
    if online:
        msStatus = await serverStatus(currentServer)
        alreadyActive = discord.Embed(
            title=serverTitle,
            description="Server already `ONLINE` with `" + str(
                msStatus.players.online) + "` people playing.",
            color=discord.Color.green())
        await botmessage.edit(embed=alreadyActive)
    else:
        hwAlive = await check_ping()
        HWActiveScreen = discord.Embed(
            title=serverTitle,
            description="Server Hardware instance active. Connecting...",
            color=discord.Color.gold())
        HWBootingScreen = discord.Embed(
            title=serverTitle,
            description="Server Hardware booting... This may take some time and it may seem like nothing is happening.",
            color=discord.Color.gold())
        HWBootFailScreen = discord.Embed(
            title=serverTitle,
            description="Server Hardware failed to boot... Please try again in a few minutes",
            color=discord.Color.red())

        if hwAlive:
            await botmessage.edit(embed=HWActiveScreen)
            await bootServer(ctx, botmessage, currentServer)
        else:
            await botmessage.edit(embed=HWBootingScreen)
            await wakePC()
            for _ in range(24):
                hwAlive = await check_ping()
                if hwAlive:
                    await bootServer(ctx, botmessage, currentServer)
                    break
                else:
                    await asyncio.sleep(5)
            if not hwAlive:
                await botmessage.edit(embed=HWBootFailScreen)


async def bootServer(ctx, botmessage, currentServer):
    serverTitle = "{0}: Server Manager".format(
        f'{currentServer.emojiStr} {currentServer.name}'
    )

    connectedSceen = discord.Embed(
        title=serverTitle,
        description="Connected! Booting server...",
        color=discord.Color.gold())
    sessionName = "{0}Server".format(currentServer.location)
    os.system("tmux new -s {0} -d".format(sessionName))
    await asyncio.sleep(1)
    os.system(
        "tmux send-keys -t {0} 'ssh {1}@{2}' Enter".format(sessionName, sshUSER, sshIP))
    await asyncio.sleep(5)
    os.system("tmux send-keys -t {0} '{1}' Enter".format(sessionName, sshPASS))
    await asyncio.sleep(1)
    await botmessage.edit(embed=connectedSceen)
    os.system(
        "tmux send-keys -t {0} '{1}' Enter".format(sessionName, defaultDrive))
    await asyncio.sleep(1)
    os.system("tmux send-keys -t {0} 'cd {1}{2}' Enter".format(
        sessionName, defaultLocation, currentServer.location))
    await asyncio.sleep(1)
    os.system("tmux send-keys -t {0} 'start.bat' Enter".format(sessionName))
    await asyncio.sleep(1)
    await onlineLoop(ctx, botmessage, currentServer)


# Loops until the server is active.
async def onlineLoop(ctx, botmessage, currentServer: server):
    serverTitle = "{0}: Server Manager".format(
        f'{currentServer.emojiStr} {currentServer.name}'
    )

    onlineScreen = discord.Embed(
        title=serverTitle,
        description="{0}: The {1} Server is Online!\n\nIP: `{2}`".format(
            ctx.message.author.mention,
            currentServer.name,
            currentServer.address),
        color=discord.Color.green())
    failedScreen = discord.Embed(
        title=serverTitle,
        description="{0}: Server failed to boot in time. Please contact <@618876946830589963>".format(
            ctx.message.author.mention,
            currentServer.name),
        color=discord.Color.dark_red())
    for _ in range(36):
        if await serverOnline(currentServer):
            await botmessage.edit(embed=onlineScreen)
            await pingUser(ctx)
            break
        await asyncio.sleep(5)
    if not await serverOnline(currentServer):
        await botmessage.edit(embed=failedScreen)


async def serverOnline(currentServer: server):
    ms = mcstatus.MinecraftServer.lookup(currentServer.address)
    try:
        ms.ping()
    except:
        return False
    return True


async def serverStatus(currentServer: server):
    try:
        ms = mcstatus.MinecraftServer.lookup(currentServer.address)
        msStatus = ms.query()
    except:
        msStatus = None
    return msStatus


async def serverSelectScreen(ctx):
    message = ctx.message
    loadingScreen = discord.Embed(
        description=f"{loadingIcon} Loading server `0/{len(servers)}`... Please wait...")
    mainScreen = discord.Embed(
        title="Server Manager",
        description="Please select a server:",
        color=discord.Color.gold())
    failScreen = discord.Embed(
        title="Server Manager",
        description="Took too long to respond. Please try again",
        color=discord.Color.dark_red())
    botmessage: discord.message = await ctx.send(embed=loadingScreen)
    currentServer = None
    for i, server in enumerate(servers):
        loadingScreen = discord.Embed(
            description=f"{loadingIcon} Loading server `{i}/{len(servers)}`... Please wait...",
        )
        await botmessage.edit(embed=loadingScreen)
        await botmessage.add_reaction(server.emojiStr)
    await botmessage.edit(embed=mainScreen)

    def check(reaction, user):
        return any(user == message.author and str(
            reaction.emoji) == server.emojiStr for server in servers)
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await botmessage.edit(embed=failScreen)
    else:
        for server in servers:
            if str(reaction.emoji) == server.emojiStr:
                currentServer = server
                break
    return botmessage, currentServer


async def stopServer(currentServer: server):
    # await recordCheatUsage(currentServer)
    sessionName = "{0}Server".format(currentServer.location)
    os.system(
        "tmux send-keys -t {0} 'say Server Shutting Down in 30s' Enter".format(sessionName))
    await asyncio.sleep(15)
    os.system(
        "tmux send-keys -t {0} 'say Server Shutting Down in 15s' Enter".format(sessionName))
    await asyncio.sleep(10)
    os.system(
        "tmux send-keys -t {0} 'say Server Shutting Down in 5s' Enter".format(sessionName))
    await asyncio.sleep(5)
    os.system(
        "tmux send-keys -t {0} 'say Server Shutting Down' Enter".format(sessionName))
    await asyncio.sleep(2)
    os.system("tmux send-keys -t {0} 'stop' Enter".format(sessionName))
    await asyncio.sleep(60)
    os.system("tmux send-keys -t {0} 'exit' Enter".format(sessionName))
    await asyncio.sleep(1)
    os.system("tmux send-keys -t {0} 'exit' Enter".format(sessionName))
    await asyncio.sleep(1)
    online = await serverOnline(currentServer)
    return not online


@tasks.loop(seconds=120)
async def update_status():
    with open("server_statuses.json", "r") as file:
        try:
            data = json.load(file)
        except:
            data = {'onlinePlayers': 0, 'onlineServers': 0}
        onlinePlayers = data["onlinePlayers"]
        onlineServers = data["onlineServers"]
    if onlinePlayers == 1:
        game = discord.Game(
            name=f" on {', '.join(onlineServers)} with {onlinePlayers} player.")
    elif onlinePlayers > 1:
        game = discord.Game(
            name=f" on {', '.join(onlineServers)} with {onlinePlayers} players.")
    elif len(onlineServers) > 0:
        game = discord.Game(name=f"on {', '.join(onlineServers)}")
    else:
        game = discord.Game("all alone :(")

    await bot.change_presence(status=discord.Status.online, activity=game)


def restart_bot(): 
    os.execv(sys.executable, ['python'] + sys.argv)


# Commands
@commands.is_owner()
@bot.command()
async def update(ctx):
    await logging(ctx, "UPDATE")
    await update_status()
    await ctx.send("Status successfully updated.")


@bot.command()
async def start(ctx):
    await logging(ctx, "START")
    botmessage, currentServer = await serverSelectScreen(ctx)
    if currentServer is not None:
        serverTitle = "{0}: Server Manager".format(
            f'{currentServer.emojiStr} {currentServer.name}'
        )

        loadingScreen = discord.Embed(
            title=serverTitle,
            description="Server Selected! Please wait...",
            color=discord.Color.gold())
        await botmessage.edit(embed=loadingScreen)
        await startServer(ctx, botmessage, currentServer)


@commands.is_owner()
@bot.command()
async def stop(ctx):
    await logging(ctx, "STOP")
    botmessage, currentServer = await serverSelectScreen(ctx)
    serverTitle = "{0}: Server Manager".format(
        f'{currentServer.emojiStr} {currentServer.name}'
    )

    shutdownScreen = discord.Embed(
        title=serverTitle,
        description="Server shutdown successfully.",
        color=discord.Color.green())
    attemptingShutdownScreen = discord.Embed(
        title=serverTitle,
        description="Attempting to shutdown the server...",
        color=discord.Color.gold())
    shutdownFailScreen = discord.Embed(
        title=serverTitle,
        description="Server failed to shutdown.",
        color=discord.Color.dark_red())
    alreadyInnactiveScreen = discord.Embed(
        title=serverTitle,
        description="This server is not online.",
        color=discord.Color.green())
    await botmessage.edit(embed=attemptingShutdownScreen)
    online = await serverOnline(currentServer)
    if online:
        success = await stopServer(currentServer)
        if success:
            await botmessage.edit(embed=shutdownScreen)
        else:
            await botmessage.edit(embed=shutdownFailScreen)
    else:
        await botmessage.edit(embed=alreadyInnactiveScreen)


@commands.is_owner()
@bot.command()
async def shutdown(ctx):
    await logging(ctx, "SHUTDOWN")
    botmessage = await ctx.send("Attempting to shutdown HWServer...")
    HWOnline = await check_ping()
    if HWOnline:
        for server in servers:
            online = await serverOnline(server)
            if online:
                await botmessage.edit(content="HWServer has online servers... Shutting those down safely first.")
                await stopServer(server)
        await botmessage.edit(content="Sending shutdown commands now...")
        sessionName = "shutdownSession"
        os.system("tmux new -s {0} -d".format(sessionName))
        await asyncio.sleep(1)
        os.system(
            "tmux send-keys -t {0} 'ssh {1}@{2}' Enter".format(sessionName, sshUSER, sshIP))
        await asyncio.sleep(1)
        os.system(
            "tmux send-keys -t {0} '{1}' Enter".format(sessionName, sshPASS))
        await asyncio.sleep(1)
        os.system(
            "tmux send-keys -t {0} 'shutdown /s' Enter".format(sessionName))
        await asyncio.sleep(1)
        os.system("tmux send-keys -t {0} 'exit' Enter".format(sessionName))
        await asyncio.sleep(1)
        os.system("tmux send-keys -t {0} 'exit' Enter".format(sessionName))
        await asyncio.sleep(1)
        await botmessage.edit(content="Sent commands... Waiting 60s for shutdown...")
        await asyncio.sleep(30)
        await botmessage.edit(content="Sent commands... Waiting 30s for shutdown...")
        await asyncio.sleep(30)
        HWOnline = await check_ping()
        if HWOnline:
            await botmessage.edit(content="FAILED TO SHUTDOWN. PLEASE TRY AGAIN.")
        else:
            await botmessage.edit(content="HWServer Shutdown Successfully!")
    else:
        await botmessage.edit(content="HWServer is already shutdown.")


@bot.command()
async def check(ctx):
    await logging(ctx, "CHECK")
    mainScreen = discord.Embed(
        title="Server Manager",
        description=f"{loadingIcon} Checking Servers... Please Wait...",
        color=discord.Color.gold())
    botmessage = await ctx.send(embed=mainScreen)
    descriptionText = ""
    HWOnline = await check_ping()
    if HWOnline:
        descriptionText += "🖥️ Server Computer: 🟢\n"
        loadingText = f"🖥️ Server Computer: {loadingIcon}\n"
        for server in servers:
            loadingText += f"{server.emojiStr} {server.name}: {loadingIcon}\n"

        statusScreen = discord.Embed(
            title="Server Manager",
            description=loadingText,
            color=discord.Color.gold())
        await botmessage.edit(embed=statusScreen)
        for server in servers:
            online = await serverOnline(server)
            if online:
                try:
                    MCServer = mcstatus.MinecraftServer.lookup(server.address)
                    msStatus = MCServer.query()
                    online = True
                except:
                    continue
                if msStatus.players.online > 0:
                    players = msStatus.players
                    playerNameList = players.names
                    playerList = ", ".join(playerNameList)
                    descriptionText += "{0} {1}: 🟢 - `{2}/{3}` - `({4})` - `{5}`\n".format(
                        server.emojiStr, server.name, str(
                            msStatus.players.online), str(
                            msStatus.players.max), playerList,
                        server.address)
                else:
                    descriptionText += "{0} {1}: 🟢 - `{2}/{3}` - `{4}`\n".format(
                        server.emojiStr, server.name, str(
                            msStatus.players.online), str(
                            msStatus.players.max),
                        server.address)
            else:
                descriptionText += "{0} {1}: 🔴\n".format(
                    server.emojiStr, server.name)
    else:
        descriptionText += "🖥️ Server Computer: 🔴\n"
        for server in servers:
            descriptionText += "{0} {1}: 🔴\n".format(server.emojiStr, server.name)
    statusScreen = discord.Embed(
        title="Server Manager",
        description=descriptionText,
        color=discord.Color.green())
    await botmessage.edit(embed=statusScreen)


@bot.command()
async def ip(ctx):
    ipText = "".join(
        "{0} {1}: `{2}`\n".format(server.emojiStr, server.name, server.address)
        for server in servers
    )
    ipScreen = discord.Embed(
        title="Server Manager",
        description=ipText,
        color=discord.Color.green()
    )
    await ctx.send(embed=ipScreen)


@bot.command()
async def ips(ctx):
    await ip(ctx)


@commands.is_owner()
@bot.command()
async def fas(ctx):
    await logging(ctx, "FAS")
    parser.read("config.ini")
    doFullShutdown = parser.get("AutoShutdown", "doFullShutdown")
    if doFullShutdown == "1":
        FASStatus = "🟢"
    else:
        FASStatus = "🔴"
    FASOptionScreen = discord.Embed(
        title="FAS Manager", description="Would you like to enable FAS?\nCurrent Status: {}".format(FASStatus))
    failScreen = discord.Embed(
        title="FAS Manager",
        description="Took too long to respond. Please try again",
        color=discord.Color.dark_red())
    botmessage = await ctx.send(embed=FASOptionScreen)
    await botmessage.add_reaction("🟢")
    await botmessage.add_reaction("🔴")
    message = ctx.message

    def check(reaction, user):
        return user == message.author and str(reaction.emoji) in {"🟢", "🔴"}
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await botmessage.edit(embed=failScreen)
    else:
        if user == message.author:
            if str(reaction.emoji) == "🟢":
                parser.set("AutoShutdown", "doFullShutdown", "1")
                with open("config.ini", "w") as configfile:
                    parser.write(configfile)
                FASStatus = "🟢"
                selectedScreen = discord.Embed(
                    title="FAS Manager", description="Current Status: {}".format(FASStatus))
                await botmessage.edit(embed=selectedScreen)
            elif str(reaction.emoji) == "🔴":
                parser.set("AutoShutdown", "doFullShutdown", "0")
                with open("config.ini", "w") as configfile:
                    parser.write(configfile)
                FASStatus = "🔴"
                selectedScreen = discord.Embed(
                    title="FAS Manager", description="Current Status: {}".format(FASStatus))
                await botmessage.edit(embed=selectedScreen)
            else:
                await ctx.send("Failed to set FAS Policy")
        parser.read("config.ini")


@commands.is_owner()
@bot.command()
async def spam(ctx, *, args):
    await logging(ctx, "SPAM")
    for _ in range(15):
        await ctx.send(args)


@commands.is_owner()
@bot.command()
async def restart(ctx):
    await ctx.send("Rebooting bot...")
    restart_bot()

@bot.command()
async def ping(ctx):
    await logging(ctx, "PING")
    await ctx.send("Pong")


@bot.command()
async def pong(ctx):
    await logging(ctx, "PONG")
    await ctx.send("Ping")


@bot.command()
async def pingpong(ctx):
    await logging(ctx, "pingpong")
    await ctx.send("Pong Ping")


@bot.command()
async def pongping(ctx):
    await logging(ctx, "pongping")
    await ctx.send("Ping Pong")


@commands.is_owner()
@bot.command()
async def kill(ctx):
    await ctx.send(f"{bot_name} says Sayonara!")
    await ctx.bot.close()


@update_status.before_loop
async def before_update_status():
    await bot.wait_until_ready()

update_status.start()
bot.run(TOKEN)
