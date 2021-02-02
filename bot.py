import asyncio
import os
import json
import smashsetfunctions
import discord
from discord.ext import commands, tasks
from jipesoclasses import SmashSet

with open("config.json") as json_data_file:
    config = json.load(json_data_file)

smashggKey = config['smashggKey']
eventId = config['eventId']
discordKey = config['discordKey']
betsChannelId = config['betsChannelId']

bot = commands.Bot(command_prefix='$')
betsChannel = None

smashSets = dict()
bets = None

@commands.command()
async def bet(ctx, arg):
    await ctx.send(arg)

@tasks.loop(seconds=2.0)
async def update_sets():
    smashsetfunctions.update_sets(smashSets, smashggKey, eventId)
    betsChannel = bot.get_channel(806053690543702037)
    for smashSetKey in smashSets:
        smashSet = smashSets[smashSetKey]
        playerKeyList = list(smashSet.players)
        if smashSet.started == False:
            await betsChannel.send('Set started with ID %s: %s(%s) vs. %s(%s)' % (smashSetKey,
                                                                            smashSet.players[playerKeyList[0]],
                                                                            playerKeyList[0],
                                                                            smashSet.players[playerKeyList[1]],
                                                                            playerKeyList[1]))
            smashSet.started = True
           
        if smashSet.ending == True and smashSet.ended == False:
            await betsChannel.send('Set ended with ID %s: %s(%s) vs. %s(%s)' % (smashSetKey,
                                                                            smashSet.players[playerKeyList[0]],
                                                                            playerKeyList[0],
                                                                            smashSet.players[playerKeyList[1]],
                                                                            playerKeyList[1]))
            smashSet.ended = True

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    update_sets.start()
    
bot.add_command(bet)
bot.run(discordKey)

print("end")
