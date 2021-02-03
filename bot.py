import atexit
import asyncio
import os
import json
import smashsetfunctions
import discord
from discord.ext import commands, tasks
from jipesoclasses import SmashSet
from jipesoclasses import Bet

with open('config.json') as json_data_file:
    config = json.load(json_data_file)

with open('jipeso.json') as json_data_file:
    jipesoUsers = json.load(json_data_file)

smashggKey = config['smashggKey']
eventId = config['eventId']
discordKey = config['discordKey']
betsChannelId = config['betsChannelId']

bot = commands.Bot(command_prefix='!')

smashSets = dict()
bets = None

def ensure_jipesoUser_exists(jipesoUserId):
    if not str(jipesoUserId) in jipesoUsers:
        jipesoUsers[str(jipesoUserId)] = {'balance' : 100}

def get_balance(jipesoUserId):
    ensure_jipesoUser_exists(jipesoUserId)
    return jipesoUsers[str(jipesoUserId)]['balance']

def set_balance(jipesoUserId, amount):
    ensure_jipesoUser_exists(jipesoUserId)
    jipesoUsers[str(jipesoUserId)]['balance'] = amount

@tasks.loop(seconds=60.0)
async def save_jipesos():
    with open('jipeso.json', 'w') as json_data_file:
        json.dump(jipesoUsers, json_data_file)
    print("Saved.")

async def calculate_bets(betsChannel, finishedSet):
    totalBetAmount = 0.0
    winnerBetAmount = 0.0
    for betKey in finishedSet.bets:
        bet = finishedSet.bets[betKey]
        totalBetAmount += bet.amount
        if bet.predictionId == finishedSet.winner:
            winnerBetAmount += bet.amount
        
    await betsChannel.send('%s won the set. %d Jipesos were side bet' % (finishedSet.players[finishedSet.winner]['name'], totalBetAmount))

    if winnerBetAmount == 0.0 or totalBetAmount == 0.0:
        return
    
    for betKey in finishedSet.bets:
        bet = finishedSet.bets[betKey]
        percentOfPot = bet.amount / winnerBetAmount
        earnings = totalBetAmount * percentOfPot
        
        beterBalance = get_balance(betKey) + earnings
        set_balance(betKey, beterBalance)
        await betsChannel.send('<@!%s> earned %d Jipesos(%d%% of pot) in bettings. Their balance is now %d' % (betKey, earnings, percentOfPot * 100, beterBalance))

    await save_jipesos()
    
@commands.command()
async def bet(ctx, predictionName, amount):
    amount = float(amount)
    beterBalance = get_balance(ctx.author.id)
    
    setToBet = None
    predictionInt = 0
    opponentInt = 0
    
    for setKey in smashSets:
        smashSet = smashSets[setKey]
        if smashSet.ended == True:
            continue
        
        counter = 0
        for playerKey in smashSet.players:
            if smashSet.players[playerKey]['name'] == predictionName:
                setToBet = smashSet
                predictionId = playerKey
                predictionInt = counter
            counter += 1
        
    if setToBet == None:
        await ctx.channel.send('<@!%s> Couldn\'t find match/player to bet on' % (ctx.author.id))
        return

    opponentInt = 1 - predictionInt
    playerKeyList = list(setToBet.players)
    opponent = setToBet.players[playerKeyList[opponentInt]]
    
    if not ctx.author.id in setToBet.bets:
        if beterBalance < amount:
            await ctx.channel.send('<@!%s> Your bet is more than your account balance (%d Jipesos)' % (ctx.author.id, beterBalance))
            return
    
        setToBet.bets[ctx.author.id] = Bet(int(predictionId), amount)
        set_balance(ctx.author.id, beterBalance - amount)
        await ctx.channel.send('<@!%s> has placed a %d Jipeso bet on %s\'s set vs. %s. Their balance is now %d Jipesos' % (ctx.author.id, amount, predictionName, opponent['name'], get_balance(ctx.author.id)))
    else:
        await ctx.channel.send('<@!%s> You already placed a bet on this set' % (ctx.author.id))

@commands.command()
async def balance(ctx):
    ensure_jipesoUser_exists(ctx.author.id)
    await ctx.channel.send('<@!%s> Your balance is %d Jipesos' % (ctx.author.id, get_balance(ctx.author.id)))

@tasks.loop(seconds=5.0)
async def update_sets():
    smashsetfunctions.update_sets(smashSets, smashggKey, eventId)
    betsChannel = bot.get_channel(806053690543702037)
    for smashSetKey in smashSets:
        smashSet = smashSets[smashSetKey]
        playerKeyList = list(smashSet.players)
        if smashSet.started == False:
            startString = '%s vs. %s has started' % (smashSet.players[playerKeyList[0]]['name'], smashSet.players[playerKeyList[1]]['name'])
            print(startString)
            await betsChannel.send(startString)
            smashSet.started = True
           
        if smashSet.ending == True and smashSet.ended == False:
            endString = '%s vs. %s has ended' % (smashSet.players[playerKeyList[0]]['name'], smashSet.players[playerKeyList[1]]['name'])
            print(endString)
            await betsChannel.send(endString)
            await calculate_bets(betsChannel, smashSet)
            smashSet.ended = True

@commands.command()
async def echo(ctx, echo):
    print(echo)
    await ctx.channel.send(echo)
    
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    update_sets.start()
    save_jipesos.start()

atexit.register(save_jipesos)
bot.add_command(bet)
bot.add_command(balance)
bot.add_command(echo)
bot.run(discordKey)
