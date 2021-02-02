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

bot = commands.Bot(command_prefix='$')
smashSets = dict()
bets = None

@commands.command()
async def bet(ctx, arg):
    await ctx.send(arg)

@tasks.loop(seconds=2.0)
async def update_sets():
    print("update")
    smashsetfunctions.update_sets(smashSets, smashggKey, eventId)
    for smashSetKey in smashSets:
        smashSet = smashSets[smashSetKey]
        if smashSet.started == False:
           smashSet.started = True
           
        if smashSet.ending == True and smashSet.ended == False:
            print(smashSet.players[smashSet.winner])
            print(smashSet.startTime)
            smashSet.ended = True
    
update_sets.start()
bot.add_command(bet)
bot.run(discordKey)

print("end")
