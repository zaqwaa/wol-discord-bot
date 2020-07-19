#!/usr/bin/env python3

import socket
import os
import asyncio
import time

import discord
from discord.ext import commands, tasks

from contextlib import closing
from wakeonlan import send_magic_packet
from dotenv import load_dotenv

from mcstatus import MinecraftServer

# load config
load_dotenv(verbose=True)
DISCORD_BOT_TOKEN=os.getenv('DISCORD_BOT_TOKEN')
MC_SERVER_MAC=os.getenv('MC_SERVER_MAC')
MC_SERVER_IP=os.getenv('MC_SERVER_IP')
MC_SERVER_WOL_IP=os.getenv('MC_SERVER_WOL_IP')
MC_SERVER_INTERFACE_PORT=int(os.getenv('MC_SERVER_INTERFACE_PORT'))
MC_SERVER_PORTS=os.getenv('MC_SERVER_PORTS')

# setup bot
client = discord.Client()

description = '''
A bot to power on a Minecraft server using Wake-On-Lan. Also provides some info about the servers
'''

bot = commands.Bot(command_prefix='$', description = description)

# ports to look for servers
server_port_list = [int(e) for e in MC_SERVER_PORTS.split(",")]

def IsPortOpen(ip, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(1)
        return not bool(sock.connect_ex((ip, int(port))))       # returns 0 for success

@bot.event
async def on_ready():
    print('We have logged in as {0}#{1}'.format(bot.user.name,bot.user.discriminator))

@bot.command()
async def hello(ctx):
    """make bot say hello"""
    await ctx.send('Hewwo! :3')

@bot.command()
async def startmcserver(ctx):
    """send a WoL packet to start the MC server"""
    await ctx.send('Sending ✨magic packet✨!')
    send_magic_packet(MC_SERVER_MAC,ip_address=MC_SERVER_WOL_IP)
    await ctx.send('Please allow ~2 minutes for the server to boot!')

@bot.command()
async def checkmcserver(ctx):
    """Check if the MC control panel interface port is open"""
    if IsPortOpen(MC_SERVER_IP, MC_SERVER_INTERFACE_PORT):
        await ctx.send("Interface port is open! Server is most likely up.")
    else:
        await ctx.send("Interface port is not open... server may be down")

@bot.command()
async def mcserverstats(ctx):
    """Check if the MC control panel interface port is open"""
    servers_online = 0
    output_message = ""
    if IsPortOpen(MC_SERVER_IP, MC_SERVER_INTERFACE_PORT):
        for port in server_port_list:
            if IsPortOpen(MC_SERVER_IP, port):
                servers_online = servers_online + 1
                mcserver = MinecraftServer(MC_SERVER_IP, port)
                status = mcserver.status()
                player_list = [player.name for player in status.players.sample] if status.players.sample is not None else ["No players connected"]
                players = ", ".join(player_list)
                server_info = "*{name}*@{ip}:{port}: {version} \n\t{players}".format(
                        name = status.description['text'],
                        ip = MC_SERVER_IP,
                        port = port,
                        version = status.version.name,
                        players = players)
                output_message = output_message + server_info + "\n"
        if(servers_online > 0):
            await ctx.send(output_message)
        else:
            await ctx.send("No servers online.")
    else:
        await ctx.send("Interface port is not open... no servers to check")

@tasks.loop(seconds=15)
async def set_bot_presence():
    if IsPortOpen(MC_SERVER_IP, MC_SERVER_INTERFACE_PORT):
        players_online = 0
        for port in server_port_list:
            if IsPortOpen(MC_SERVER_IP, port):
                mcserver = MinecraftServer(MC_SERVER_IP, port)
                status = mcserver.status()
                players_online = players_online + status.players.online
        game = discord.Game("Server is up! {0} player{1} online".format(players_online, "s" if players_online != 1 else ""))
        await bot.change_presence(status=discord.Status.online,activity=game)
    else:
        game = discord.Game("Server is down.")
        await bot.change_presence(status=discord.Status.idle,activity=game)

@set_bot_presence.before_loop
async def before_set_bot_presence():
    await bot.wait_until_ready()

set_bot_presence.start()
bot.run(DISCORD_BOT_TOKEN)