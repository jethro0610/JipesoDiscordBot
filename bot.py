import datetime
import json
import smashsetfunctions
import discord
from discord.ext import commands, tasks

from jipesoclasses import SmashSet
from jipesoclasses import Bet

from jipesoclasses import load_gg_id_json
from jipesoclasses import save_gg_id_json
from jipesoclasses import load_jipeso_user_json
from jipesoclasses import save_jipeso_user_json

from jipesoclasses import add_gg_id_to_jipeso_user
from jipesoclasses import get_jipeso_user_from_gg_id
from jipesoclasses import get_jipeso_user_from_discord_id

from jipesoclasses import mention_to_gg_id
from jipesoclasses import gg_id_to_discord_id

from jipesoclasses import set_winners_pay
from jipesoclasses import set_losers_pay

config = None
payouts = None
phase_group_id = None
bracket_link = ''
smash_sets = dict()

with open('config.json') as json_data_file:
    config = json.load(json_data_file)
with open('payouts.json') as json_data_file:
    payouts = json.load(json_data_file)

smashgg_key = config['smashgg_key']
discord_key = config['discord_key']
bets_channel_id = config['bets_channel_id']

set_winners_pay(float(config['winners_pay']))
set_losers_pay(float(config['losers_pay']))

max_bet_time = config['max_bet_time']
jipeso_text = 'Jipeso'

load_jipeso_user_json()
load_gg_id_json()

bot = commands.Bot(command_prefix='!')

@tasks.loop(seconds=120.0)
async def save_jipeso_user_json_loop():
    save_jipeso_user_json()

@tasks.loop(seconds=5.0)
async def update_sets():
    global phase_group_id
    global smash_sets
    global smashgg_key
    
    if phase_group_id == None:
        return
    
    smashsetfunctions.update_sets(smash_sets, smashgg_key, phase_group_id)
    bets_channel = bot.get_channel(int(bets_channel_id))
    for smash_set_key in smash_sets:
        smash_set = smash_sets[smash_set_key]
        if smash_set.started == False:
            smash_set.startTime = int(datetime.datetime.now().timestamp())
            start_string = '%s vs. %s started' % (smash_set.players[0].get_player_string(), smash_set.players[1].get_player_string())
            print(start_string)
            await bets_channel.send(start_string)
            smash_set.started = True
           
        if smash_set.ending == True and smash_set.ended == False:
            end_string = '%s vs. %s ended' % (smash_set.players[0].get_player_string(), smash_set.players[1].get_player_string())
            print(end_string)
            await bets_channel.send(end_string)
            
            bet_text_outputs = smash_set.end(jipeso_text)
            for text_output in bet_text_outputs:
                await bets_channel.send(text_output)

@commands.command()
async def bet(ctx, prediction_input, amount):
    global smash_sets

    beter = get_jipeso_user_from_discord_id(ctx.author.id)
    amount = amount.replace('-','')
    amount = float(amount)
    
    set_to_bet = None
    prediction_int = 0
    opponent_int = 0

    prediction_gg_id = ''
    if '<' in prediction_input and '>' in prediction_input and '@' in prediction_input:
        prediction_gg_id = mention_to_gg_id(prediction_input)
    
    for set_key in smash_sets:
        smash_set = smash_sets[set_key]
        if smash_set.ended == True:
            continue
        
        counter = 0
        for player in smash_set.players:
            if player.name == prediction_input or player.gg_id == prediction_gg_id:
                set_to_bet = smash_set
                predictionId = player.set_id
                prediction_int = counter
            counter += 1
        
    if set_to_bet == None:
        await ctx.channel.send('<@!%s> Couldn\'t find match/player to bet on' % (ctx.author.id))
        return
    
    if int(datetime.datetime.now().timestamp()) - set_to_bet.startTime > max_bet_time:
        await ctx.channel.send('<@!%s> Too late to bet on this set' % (ctx.author.id))
        return
    
    opponent_int = 1 - prediction_int
    opponent = set_to_bet.players[opponent_int]
    prediction = set_to_bet.players[prediction_int]
    
    if not ctx.author.id in set_to_bet.bets:
        if beter.balance < amount:
            await ctx.channel.send('<@!%s> Your bet is more than your account balance (%s%d)' % (ctx.author.id, jipeso_text, beter.balance))
            return
    
        set_to_bet.bets.append(Bet(beter, prediction, amount))
        beter.balance -= amount
        print('User %s placed a %d Jipeso bet on %s set vs. %s.' %(ctx.author.id, amount, prediction.name, opponent.name))
        await ctx.channel.send('<@!%s> placed a %s%d bet on %s\'s set vs. %s. Their balance is now %s%d' %  (ctx.author.id,
                                                                                                            jipeso_text,
                                                                                                            amount,
                                                                                                            prediction.get_player_string(),
                                                                                                            opponent.get_player_string(),
                                                                                                            jipeso_text,
                                                                                                            beter.balance))
    else:
        await ctx.channel.send('<@!%s> You already placed a bet on this set' % (ctx.author.id))
    save_jipeso_user_json()
    
@commands.command()
async def balance(ctx):
    await ctx.channel.send('<@!%s> Your balance is %s%d' % (ctx.author.id, jipeso_text, get_jipeso_user_from_discord_id(ctx.author.id).balance))

@commands.command()
async def linkgg(ctx, gg_id_slug):
    gg_id = str(smashsetfunctions.get_gg_id(gg_id_slug, smashgg_key))
    if gg_id == None:
        await ctx.channel.send('<@!%s> Couldn\'t find account to link to' % ctx.author.id)
        return

    add_gg_result = add_gg_id_to_jipeso_user(gg_id, ctx.author.id)
    if add_gg_result == 1:
        print('User %s linked to SmashGG ID %s' %(ctx.author.id, gg_id))
        await ctx.channel.send('<@!%s> SmashGG linked succesfully!' % ctx.author.id)
    elif add_gg_result == -1:
        await ctx.channel.send('<@!%s> SmashGG already linked to another Discord user' % ctx.author.id)
    else:
        await ctx.channel.send('<@!%s> Discord already linked to a SmashGG account' % ctx.author.id)

@commands.command()
async def starttourney(ctx, tourney_id):
    global phase_group_id
    global bracket_link
    
    if phase_group_id != None:
        await ctx.channel.send('There\'s already an active tournament')
        return
    
    if ctx.message.author.guild_permissions.administrator == False:
        return
    
    phase_group_json, bracket_link = smashsetfunctions.get_event_standings(tourney_id, smashgg_key)
    if(phase_group_json == None):
        await ctx.channel.send('Tournament not found')
        return

    phase_group_id = tourney_id
    tourney_name = phase_group_json['phase']['event']['tournament']['name']
    event_name = phase_group_json['phase']['event']['name']

    print('Started Tournament: ' + tourney_name + ' | ' + event_name)
    await ctx.channel.send('Started Tournament: ' + tourney_name + ' | ' + event_name + '\n' + bracket_link)
    
@commands.command()
async def stoptourney(ctx):
    global phase_group_id
    global bracket_link
    
    if phase_group_id == None:
        await ctx.channel.send('There\'s no active tournament')
        return
    
    if ctx.message.author.guild_permissions.administrator == False:
        return

    print('Tournament ended')
    await ctx.channel.send('Tournament over')
    bracket_link = ''
    phase_group_id = None

@commands.command()
async def stoptourneyresults(ctx):
    global phase_group_id
    global bracket_link
    
    if phase_group_id == None:
        await ctx.channel.send('There\'s no active tournament')
        return
    
    if ctx.message.author.guild_permissions.administrator == False:
        return

    await pay_results(ctx.channel)
    bracket_link = ''
    phase_group_id = None

async def pay_results(message_channel):
    global phase_group_id
    global smashgg_key
    
    phase_group_json, bracket_link = smashsetfunctions.get_event_standings(phase_group_id, smashgg_key)
    event_json = phase_group_json['phase']['event']
    results_json = phase_group_json['standings']['nodes']

    tourney_name = event_json['tournament']['name']
    event_name = event_json['name']
    total_entrants = event_json['numEntrants']
    total_pot = total_entrants * 150
    
    output_string = tourney_name + ' | ' + event_name + ' | Total Entrants: ' + str(total_entrants) + ' | Total Pot: ' + str(jipeso_text) + str(total_pot) + '\n'
    for result in results_json:
        placement = str(result['placement'])
        
        result_player = Player(result['entrant']['participants'][0]['player']['gamerTag'], str(result['entrant']['participants'][0]['player']['id']))
        output_string += placement + '. ' + result_player.get_player_string()
        
        payout_percent = 0
        if placement in payouts:
            payout_percent = float(payouts[placement])
        total_payout = total_pot * (payout_percent/100)
        
        result_jipeso_user = get_jipeso_user_from_gg_id(player.gg_id)
        if result_jipeso_user != None and total_payout != 0:
            result_jipeso_user.balance += total_payout
            output_string += ' (%s%s | Balance: %s%d)' % (total_payout, jipeso_text, jipeso_text, result_jipeso_user.balance)
            print('Payed out User %d Jipesos to %s for ranking %d in the tournament' % (total_payout, result_jipeso_user.discord_id, placement))

        output_string += '\n'

    save_jipeso_user_json()
    await message_channel.send(output_string)

@commands.command()
async def bracket(ctx):
    global bracket_link
    if bracket_link == '':
        await ctx.channel.send('<@!%s> There\'s no active tournament' % ctx.author.id)
        return

    await ctx.channel.send('<@!%s> %s' % (ctx.author.id, bracket_link))

@commands.command()
async def pay(ctx, reciever_id, amount):
    payer_id = str(ctx.author.id)
    reciever_id = str(reciever_id)
    reciever_id = reciever_id.replace('<', '')
    reciever_id = reciever_id.replace('@', '')
    reciever_id = reciever_id.replace('!', '')
    reciever_id = reciever_id.replace('>', '')
    amount = amount.replace('-','')
    amount = float(amount)

    try:
        await bot.fetch_user(reciever_id)
    except:
        await ctx.channel.send('<@!%s> Member not found' % (payer_id))
        return
    
    get_jipeso_user_from_discord_id(payer_id).balance -= amount
    get_jipeso_user_from_discord_id(payer_id).balance += amount

    print('User %s paid User %s %d Jipesos' % (payer_id, reciever_id, amount))
    await ctx.channel.send('<@!%s> paid <@!%s> %s%d' % (payer_id, reciever_id, jipeso_text, amount))
    save_jipeso_user_json()

@bot.event
async def on_ready():
    global jipeso_text
    print(f'{bot.user} has connected to Discord!')
    update_sets.start()
    save_jipeso_user_json_loop.start()
    jipeso_text = discord.utils.get(bot.emojis, name='jipeso')

bot.add_command(bet)
bot.add_command(balance)
bot.add_command(starttourney)
bot.add_command(stoptourney)
bot.add_command(stoptourneyresults)
bot.add_command(bracket)
bot.add_command(linkgg)
bot.add_command(pay)
bot.run(discord_key)
