import atexit
import asyncio
import os
import json
import smashsetfunctions
import discord
from discord.ext import commands, tasks
from jipesoclasses import SmashSet
from jipesoclasses import Bet

config = None
jipesoUsers = None
ggIds = None
payouts = None
phaseGroupId = None
bracketLink = ''
smashSets = dict()

with open('config.json') as json_data_file:
    config = json.load(json_data_file)

with open('jipeso.json') as json_data_file:
    jipesoUsers = json.load(json_data_file)

with open('ggIds.json') as json_data_file:
    ggIds = json.load(json_data_file)

with open('payouts.json') as json_data_file:
    payouts = json.load(json_data_file)

smashggKey = config['smashggKey']
discordKey = config['discordKey']
betsChannelId = config['betsChannelId']
winnersPay = config['winnersPay']
losersPay = config['losersPay']
jipesoText = 'Jipeso'

bot = commands.Bot(command_prefix='!')

def get_mention(jipesoId):
    return '<@!%s>' % jipesoId

def get_player_string(player):
    playerJipesoId = ggId_to_jipesoId(player['ggId'])
    if playerJipesoId != None:
        return get_mention(playerJipesoId)
    else:
        return player['name']

def mention_to_ggId(mention):
    global ggIds
    mention = mention.replace('<', '')
    mention = mention.replace('@', '')
    mention = mention.replace('!', '')
    mention = mention.replace('>', '')

    key_list = list(ggIds.keys())
    val_list = list(ggIds.values())

    if not mention in val_list:
        print("Couldn't find ggId from mention")
        return

    return str(key_list[val_list.index(mention)])
    
def ggId_to_jipesoId(ggId):
    global ggIds
    if str(ggId) in ggIds:
        return ggIds[str(ggId)]
    else:
        return None

def ensure_jipesoUser_exists(jipesoUserId):
    global jipesoUsers
    if not str(jipesoUserId) in jipesoUsers:
        jipesoUsers[str(jipesoUserId)] = {'balance' : 100}

def get_balance(jipesoUserId):
    global jipesoUsers
    ensure_jipesoUser_exists(jipesoUserId)
    return jipesoUsers[str(jipesoUserId)]['balance']

def set_balance(jipesoUserId, amount):
    global jipesoUsers
    ensure_jipesoUser_exists(jipesoUserId)
    jipesoUsers[str(jipesoUserId)]['balance'] = amount

def add_balance(jipesoUserId, amount):
    global jipesoUsers
    
    ensure_jipesoUser_exists(jipesoUserId)
    jipesoUsers[str(jipesoUserId)]['balance'] = jipesoUsers[str(jipesoUserId)]['balance'] + amount
    
@tasks.loop(seconds=120.0)
async def save_jipesos_loop():
    save_jipesos()

def save_jipesos():
    global jipesoUsers
    with open('jipeso.json', 'w') as json_data_file:
        json.dump(jipesoUsers, json_data_file)
    print("Saved.")
    
async def calculate_bets(betsChannel, finishedSet):
    totalBetAmount = 0.0
    winnerBetAmount = 0.0
    winnerInt = None
    loserInt = None
    counter = 0
    
    for betKey in finishedSet.bets:
        bet = finishedSet.bets[betKey]
        totalBetAmount += bet.amount
        if bet.predictionId == finishedSet.winner:
            winnerBetAmount += bet.amount

    for player in finishedSet.players:
        if player == finishedSet.winner:
            winnerInt = counter
        counter += 1

    loserInt = 1 - winnerInt
    playerKeyList = list(finishedSet.players)
    losingPlayer = finishedSet.players[playerKeyList[loserInt]]
    winningPlayer = finishedSet.players[playerKeyList[winnerInt]]
    
    await betsChannel.send('%s won the set. %s%d were side bet' % (get_player_string(winningPlayer), jipesoText, totalBetAmount))

    winnerJipesoId = ggId_to_jipesoId(winningPlayer['ggId'])
    if winnerJipesoId != None:
        add_balance(winnerJipesoId, winnersPay)
        await betsChannel.send('%s earned %s%d for winning' % (get_mention(winnerJipesoId), jipesoText, winnersPay))

    loserJipesoId = ggId_to_jipesoId(losingPlayer['ggId'])
    if loserJipesoId != None:
        add_balance(loserJipesoId, losersPay)
        await betsChannel.send('%s earned %s%d for trying' % (get_mention(loserJipesoId), jipesoText, losersPay))
        
    if winnerBetAmount == 0.0 or totalBetAmount == 0.0:
        return
    
    for betKey in finishedSet.bets:
        bet = finishedSet.bets[betKey]
        percentOfPot = bet.amount / winnerBetAmount
        earnings = totalBetAmount * percentOfPot
        
        beterBalance = get_balance(betKey) + earnings
        set_balance(betKey, beterBalance)
        await betsChannel.send('<@!%s> earned %s%d (%d%% of pot) in bettings. Their balance is now %s%d' % (betKey, jipesoText, earnings, percentOfPot * 100, jipesoText, beterBalance))

    save_jipesos()
    
@commands.command()
async def bet(ctx, predictionName, amount):
    global smashSets
    
    amount = float(amount)
    beterBalance = get_balance(ctx.author.id)
    
    setToBet = None
    predictionInt = 0
    opponentInt = 0

    predictionGGId = 'fill'
    if '<' in predictionName and '>' in predictionName and '@' in predictionName:
        predictionGGId = mention_to_ggId(predictionName)
    
    for setKey in smashSets:
        smashSet = smashSets[setKey]
        if smashSet.ended == True:
            continue
        
        counter = 0
        for playerKey in smashSet.players:
            if smashSet.players[playerKey]['name'] == predictionName or smashSet.players[playerKey]['ggId'] == predictionGGId:
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
    prediction = setToBet.players[playerKeyList[predictionInt]]
    
    if not ctx.author.id in setToBet.bets:
        if beterBalance < amount:
            await ctx.channel.send('<@!%s> Your bet is more than your account balance (%s%d)' % (ctx.author.id, jipesoText, beterBalance))
            return
    
        setToBet.bets[ctx.author.id] = Bet(int(predictionId), amount)
        set_balance(ctx.author.id, beterBalance - amount)
        await ctx.channel.send('<@!%s> has placed a %s%d bet on %s\'s set vs. %s. Their balance is now %s%d' % (ctx.author.id,
                                                                                                                        jipesoText,
                                                                                                                        amount,
                                                                                                                        get_player_string(prediction),
                                                                                                                        get_player_string(opponent),
                                                                                                                        jipesoText,
                                                                                                                        get_balance(ctx.author.id)))
    else:
        await ctx.channel.send('<@!%s> You already placed a bet on this set' % (ctx.author.id))

@commands.command()
async def balance(ctx):
    ensure_jipesoUser_exists(ctx.author.id)
    await ctx.channel.send('<@!%s> Your balance is %s%d' % (ctx.author.id, jipesoText, get_balance(ctx.author.id)))

@tasks.loop(seconds=5.0)
async def update_sets():
    global phaseGroupId
    global smashSets
    global smashggKey
    
    if phaseGroupId == None:
        return
    
    smashsetfunctions.update_sets(smashSets, smashggKey, phaseGroupId)
    betsChannel = bot.get_channel(int(betsChannelId))
    for smashSetKey in smashSets:
        smashSet = smashSets[smashSetKey]
        playerKeyList = list(smashSet.players)
        if smashSet.started == False:
            startString = '%s vs. %s has started' % (get_player_string(smashSet.players[playerKeyList[0]]), get_player_string(smashSet.players[playerKeyList[1]]))
            print(startString)
            await betsChannel.send(startString)
            smashSet.started = True
           
        if smashSet.ending == True and smashSet.ended == False:
            endString = '%s vs. %s has ended' % (get_player_string(smashSet.players[playerKeyList[0]]), get_player_string(smashSet.players[playerKeyList[1]]))
            print(endString)
            await betsChannel.send(endString)
            await calculate_bets(betsChannel, smashSet)
            smashSet.ended = True

@commands.command()
async def linkgg(ctx, ggSlug):
    global ggIds
    
    ggId = str(smashsetfunctions.get_gg_id(ggSlug, smashggKey))
    if ggId != None:
        if ggId in ggIds:
            await ctx.channel.send('<@!%s> Has already been linked to another Discord user' % ctx.author.id)
        else:
            ggIds[ggId] = str(ctx.author.id)
            await ctx.channel.send('<@!%s> SmashGG linked succesfully!' % ctx.author.id)
    else:
        await ctx.channel.send('<@!%s> Couldn\'t find account to link to' % ctx.author.id)
        
    with open('ggIds.json', 'w') as json_data_file:
        json.dump(ggIds, json_data_file)

async def pay_results(messageChannel):
    global phaseGroupId
    global smashggKey
    phaseGroupJson, bracketLink = smashsetfunctions.get_event_standings(phaseGroupId, smashggKey)
    eventJson = phaseGroupJson['phase']['event']
    resultsJson = phaseGroupJson['standings']['nodes']

    tourneyName = eventJson['tournament']['name']
    eventName = eventJson['name']
    totalEntrants = eventJson['numEntrants']
    totalPot = totalEntrants * 150
    
    outputString = tourneyName + ' | ' + eventName + ' | Total Entrants: ' + str(totalEntrants) + ' | Total Pot: ' + str(jipesoText) + str(totalPot) + '\n'
    for result in resultsJson:
        placement = str(result['placement'])
        player = { 'name' : result['entrant']['participants'][0]['player']['gamerTag'], 'ggId' : str(result['entrant']['participants'][0]['player']['id'])}
        outputString += placement + '. ' + get_player_string(player)
        
        payoutPercent = 0
        if placement in payouts:
            payoutPercent = float(payouts[placement])
        totalPayout = totalPot * (payoutPercent/100)
        
        playerJipesoId = ggId_to_jipesoId(player['ggId'])
        if playerJipesoId != None and totalPayout != 0:
            add_balance(playerJipesoId, totalPayout)
            outputString += ' (%s%s | Balance: %s%d)' % (totalPayout, jipesoText, jipesoText, get_balance(playerJipesoId))

        outputString += '\n'

    save_jipesos()
    await messageChannel.send(outputString)

@commands.command()
async def starttourney(ctx, newId):
    global phaseGroupId
    global bracketLink
    
    if phaseGroupId != None:
        await ctx.channel.send('There\'s already an active tournament')
        return
    
    if ctx.message.author.guild_permissions.administrator == False:
        return
    
    phaseGroupJson, bracketLink = smashsetfunctions.get_event_standings(newId, smashggKey)
    if(phaseGroupJson == None):
        await ctx.channel.send('Tournament not found')
        return

    phaseGroupId = newId
    tourneyName = phaseGroupJson['phase']['event']['tournament']['name']
    eventName = phaseGroupJson['phase']['event']['name']

    await ctx.channel.send('Started Tournament: ' + tourneyName + ' | ' + eventName + '\n' + bracketLink)
    
@commands.command()
async def stoptourney(ctx):
    global phaseGroupId
    global bracketLink
    
    if phaseGroupId == None:
        await ctx.channel.send('There\'s no active tournament')
        return
    
    if ctx.message.author.guild_permissions.administrator == False:
        return

    await ctx.channel.send('Tournament over')
    bracketLink = ''
    phaseGroupId = None

@commands.command()
async def stoptourneyresults(ctx):
    global phaseGroupId
    global bracketLink
    
    if phaseGroupId == None:
        await ctx.channel.send('There\'s no active tournament')
        return
    
    if ctx.message.author.guild_permissions.administrator == False:
        return

    await pay_results(ctx.channel)
    bracketLink = ''
    phaseGroupId = None

@commands.command()
async def bracket(ctx):
    global bracketLink
    if bracketLink == '':
        await ctx.channel.send('<@!%s> There\'s no active tournament' % ctx.author.id)
        return

    await ctx.channel.send('<@!%s> %s' % (ctx.author.id, bracketLink))

    
@bot.event
async def on_ready():
    global jipesoText
    print(f'{bot.user} has connected to Discord!')
    update_sets.start()
    save_jipesos_loop.start()
    jipesoText = discord.utils.get(bot.emojis, name='jipeso')

atexit.register(save_jipesos)
bot.add_command(bet)
bot.add_command(balance)
bot.add_command(starttourney)
bot.add_command(stoptourney)
bot.add_command(stoptourneyresults)
bot.add_command(bracket)
bot.add_command(linkgg)
bot.run(discordKey)
