import asyncio
import os
import json
import smashsetfunctions
import discord
from discord.ext import commands, tasks
from jipesoclasses import SmashSet
from jipesoclasses import Bet

with open("config.json") as json_data_file:
    config = json.load(json_data_file)

smashggKey = config['smashggKey']
eventId = config['eventId']
discordKey = config['discordKey']
betsChannelId = config['betsChannelId']

bot = commands.Bot(command_prefix='$')

smashSets = dict()
bets = None

async def calculate_bets(betsChannel, finishedSet):
    totalBetAmount = 0.0
    winnerBetAmount = 0.0
    for betKey in finishedSet.bets:
        bet = finishedSet.bets[betKey]
        totalBetAmount += bet.amount
        if(bet.predictionId == finishedSet.winner):
            winnerBetAmount += bet.amount
        
    await betsChannel.send('%s won the set. %d Jipesos were side bet' % (finishedSet.players[finishedSet.winner], totalBetAmount))
    for betKey in finishedSet.bets:
        bet = finishedSet.bets[betKey]
        percentOfPot = bet.amount / winnerBetAmount
        earnings = totalBetAmount * percentOfPot
        await betsChannel.send('<@%s> earned %d Jipesos(%d%% of pot) in bettings' % (betKey, earnings, percentOfPot * 100))
        
@commands.command()
async def betIDs(ctx, setId, predictionId, amount):
    if not int(setId) in smashSets:
        await ctx.channel.send('<@%s> Invalid set ID' % (ctx.author.id))
        return

    setToBet = smashSets[int(setId)]
    if not ctx.author.id in setToBet.bets:
        if int(predictionId) in setToBet.players:
            setToBet.bets[ctx.author.id] = Bet(int(predictionId), int(amount))
            await ctx.channel.send('<@%s> has placed a %d Jipeso bet on set %d' % (ctx.author.id, int(amount), int(setId)))
        else:
            await ctx.channel.send('<@%s> Invalid player ID' % (ctx.author.id))
    else:
        await ctx.channel.send('<@%s> You already placed a bet on this set' % (ctx.author.id))

@commands.command()
async def bet(ctx, predictionName, amount):
    setToBet = None
    predictionInt = 0
    opponentInt = 0
    
    for setKey in smashSets:
        smashSet = smashSets[setKey]
        counter = 0
        for playerKey in smashSet.players:
            if smashSet.players[playerKey] == predictionName:
                setToBet = smashSet
                predictionId = playerKey
                predictionInt = counter
            counter += 1
        
    if setToBet == None:
        await ctx.channel.send('<@%s> Couldn\'t find match/player to bet on' % (ctx.author.id, int(amount), predictionName))
        return

    opponentInt = 1 - predictionInt
    playerKeyList = list(smashSet.players)
    
    if not ctx.author.id in setToBet.bets:
        setToBet.bets[ctx.author.id] = Bet(int(predictionId), int(amount))
        await ctx.channel.send('<@%s> has placed a %d Jipeso bet on %s\'s set vs. %s' % (ctx.author.id, int(amount), predictionName, smashSet.players[playerKeyList[opponentInt]]))
    else:
        await ctx.channel.send('<@%s> You already placed a bet on this set' % (ctx.author.id))

@tasks.loop(seconds=5.0)
async def update_sets():
    smashsetfunctions.update_sets(smashSets, smashggKey, eventId)
    betsChannel = bot.get_channel(806053690543702037)
    for smashSetKey in smashSets:
        smashSet = smashSets[smashSetKey]
        playerKeyList = list(smashSet.players)
        if smashSet.started == False:
            startString = '%s vs. %s has started' % (smashSet.players[playerKeyList[0]], smashSet.players[playerKeyList[1]])
            print(startString)
            await betsChannel.send(startString)
            smashSet.started = True
           
        if smashSet.ending == True and smashSet.ended == False:
            endString = '%s vs. %s has ended' % (smashSet.players[playerKeyList[0]], smashSet.players[playerKeyList[1]])
            print(endString)
            await betsChannel.send(endString)
            await calculate_bets(betsChannel, smashSet)
            smashSet.ended = True

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    update_sets.start()
    
bot.add_command(betIDs)
bot.add_command(bet)
bot.run(discordKey)

print("end")
