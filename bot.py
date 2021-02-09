import datetime
import json
import discord
from discord.ext import commands, tasks

import smashsetfunctions
from jipesoclasses import Bet
from jipesoclasses import Player
from jipesoclasses import SmashSet

from jipesoclasses import load_gg_id_json
from jipesoclasses import save_gg_id_json
from jipesoclasses import load_jipeso_user_json
from jipesoclasses import save_jipeso_user_json

from jipesoclasses import add_gg_id_to_jipeso_user
from jipesoclasses import get_jipeso_user_from_gg_id
from jipesoclasses import get_jipeso_user_from_discord_id
from jipesoclasses import get_jipeso_user_from_mention
from jipesoclasses import mention_to_gg_id
from jipesoclasses import gg_id_to_discord_id
from jipesoclasses import discord_id_to_gg_id

from jipesoclasses import set_winners_pay
from jipesoclasses import set_losers_pay
from jipesoclasses import get_sorted_users

# Create the bot
bot = commands.Bot(command_prefix='!')

config = None
payouts = None
bot.phase_group_id = None
bot.bracket_link = ''
bot.smash_sets = dict()
bot.challenge_sets = []

# Load the configs
with open('config.json') as json_data_file:
    config = json.load(json_data_file)
with open('payouts.json') as json_data_file:
    payouts = json.load(json_data_file)

# Assign the config values
bot.smashgg_key = config['smashgg_key']
discord_key = config['discord_key']
bets_channel_id = config['bets_channel_id']
set_winners_pay(float(config['winners_pay']))
set_losers_pay(float(config['losers_pay']))
max_bet_time = config['max_bet_time']
bot.jipeso_text = 'Jipeso'

# Load user data
load_jipeso_user_json()
load_gg_id_json()

@tasks.loop(seconds=1800.0)
async def save_jipeso_user_json_loop():
    save_jipeso_user_json()

@commands.command()
async def challenge(ctx, opponent_mention, amount):
    # Make sure the amount is positive and round it to two decimals
    amount = amount.replace('-','')
    amount = float(amount)
    amount = round(amount, 2)

    # Get the challenger and opponent users
    challenger = get_jipeso_user_from_discord_id(ctx.author.id)
    opponent = get_jipeso_user_from_mention(opponent_mention)

    if challenger.discord_id == opponent.discord_id:
        await ctx.channel.send('<@!%s> Your can\'t challenge yourself' % ctx.author.id)
        return

    if amount > challenger.balance:
        await ctx.channel.send('<@!%s> Your wager is more than your account balance [%s%s]' % (ctx.author.id, bot.jipeso_text, '{:.2f}'.format(challenger.balance)))
        return

    # Skip if one of the players is already playing a set
    for smash_set_key in bot.smash_sets:
        smash_set = bot.smash_sets[smash_set_key]
        for player in smash_set.players:
            if player.get_jipeso_user().discord_id == challenger.discord_id:
                await ctx.channel.send('<@!%s> You are already in a set' % ctx.author.id)
                return
            if player.get_jipeso_user().discord_id == opponent.discord_id:
                await ctx.channel.send('<@!%s> Opponent is already in a set' % ctx.author.id)
                return

    # Skip of one of the players is being challenged
    for challenge_set in bot.challenge_sets:
        for player in challenge_set.players:
            if player.get_jipeso_user().discord_id == challenger.discord_id:
                await ctx.channel.send('<@!%s> You are already being challenged' % ctx.author.id)
                return
            if player.get_jipeso_user().discord_id == opponent.discord_id:
                await ctx.channel.send('<@!%s> Opponent is already being challenged' % ctx.author.id)
                return

    # Create the player objects for the set
    challenging_player = Player('DISCORD PLAYER', challenger.discord_id, challenger.discord_id)
    opponent_player = Player('DISCORD PLAYER', opponent.discord_id, opponent.discord_id)
    challenging_player.jipeso_user = challenger
    opponent_player.jipeso_user = opponent

    # Create the new set and add it to the challenges queue
    new_challenge_set = SmashSet()
    new_challenge_set.players.append(challenging_player)
    new_challenge_set.players.append(opponent_player)
    new_challenge_set.wager = amount
    bot.challenge_sets.append(new_challenge_set)
    challenger.balance -= amount
    save_jipeso_user_json()
    await ctx.channel.send('<@!%s> challenged <@!%s> to a match for [-%s%s]' % (challenger.discord_id, opponent.discord_id, bot.jipeso_text, '{:.2f}'.format(amount)))

@commands.command()
async def accept(ctx):
    for challenge_set in bot.challenge_sets:
        accepting_user = challenge_set.players[1].get_jipeso_user()
        opponent_user = challenge_set.players[0].get_jipeso_user()
        if accepting_user.discord_id == str(ctx.author.id):
            if challenge_set.wager > accepting_user.balance:
                await ctx.channel.send('<@!%s> The wager is more than your account balance [%s%s]' % (ctx.author.id, bot.jipeso_text, '{:.2f}'.format(accepting_user.balance)))
                return

            bot.challenge_sets.remove(challenge_set)
            bot.smash_sets['ds' + str(len(bot.smash_sets))] = challenge_set
            accepting_user.balance -= challenge_set.wager
            await ctx.channel.send('<@!%s> accepted <@!%s>\'s challenge for [-%s%s]' %   (accepting_user.discord_id, 
                                                                                        opponent_user.discord_id, 
                                                                                        bot.jipeso_text,
                                                                                        '{:.2f}'.format(challenge_set.wager)))
            save_jipeso_user_json()
            return

@commands.command()
async def decline(ctx):
    for challenge_set in bot.challenge_sets:
        declining_user = challenge_set.players[1].get_jipeso_user()
        opponent_user = challenge_set.players[0].get_jipeso_user()
        if declining_user.discord_id == str(ctx.author.id):
            bot.challenge_sets.remove(challenge_set)
            opponent_user.balance += challenge_set.wager
            await ctx.channel.send('<@!%s> declined <@!%s>\'s challenge. Refunded [+%s%s]' %   (declining_user.discord_id, 
                                                                                        opponent_user.discord_id, 
                                                                                        bot.jipeso_text,
                                                                                        '{:.2f}'.format(challenge_set.wager)))
            save_jipeso_user_json()
            return

@commands.command()
async def reportwin(ctx):
    for smash_set_key in bot.smash_sets:
        smash_set = bot.smash_sets[smash_set_key]
        for player in smash_set.players:
            if player.get_jipeso_user().discord_id == str(ctx.author.id) and smash_set.wager != -1:
                smash_set.winner_set_id = str(ctx.author.id)
                smash_set.ending = True
                return

@commands.command()
async def bet(ctx, prediction_input, amount):
    # Make sure the amount is positive and round it to two decimals
    amount = amount.replace('-','')
    amount = float(amount)
    amount = round(amount, 2)
    
    # Assign initial values
    beter = get_jipeso_user_from_discord_id(ctx.author.id)
    set_to_bet = None
    prediction_int = 0
    opponent_int = 0

    # Assign the predictions SmashGG ID if possible
    if '<' in prediction_input and '>' in prediction_input and '@' in prediction_input:
        prediction_input  = prediction_input.replace('<', '')
        prediction_input  = prediction_input.replace('@', '')
        prediction_input  = prediction_input.replace('!', '')
        prediction_input  = prediction_input.replace('>', '')

    # Find the set to bet on
    for set_key in bot.smash_sets:
        smash_set = bot.smash_sets[set_key]
        if smash_set.ended == True:
            continue

        # Find the predicted winner
        counter = 0
        for player in smash_set.players:
            if player.name == prediction_input:
                set_to_bet = smash_set
                prediction_int = counter
            elif player.get_jipeso_user() != None:
                if player.get_jipeso_user().discord_id == prediction_input:
                    set_to_bet = smash_set
                    prediction_int = counter
            counter += 1

    if set_to_bet == None:
        await ctx.channel.send('<@!%s> Couldn\'t find match/player to bet on' % (ctx.author.id))
        return

    # Skip if it's too late to bet
    if int(datetime.datetime.now().timestamp()) - set_to_bet.startTime > max_bet_time:
        await ctx.channel.send('<@!%s> Too late to bet on this set' % (ctx.author.id))
        return

    # Get the predicted winner and their opponent
    opponent_int = 1 - prediction_int
    opponent = set_to_bet.players[opponent_int]
    prediction = set_to_bet.players[prediction_int]

    # Ensure the set hasn't already been bet on
    if not set_to_bet.discord_id_has_bet(ctx.author.id):
        if beter.balance < amount:
            await ctx.channel.send('<@!%s> Your bet is more than your account balance [%s%s]' % (ctx.author.id, bot.jipeso_text, '{:.2f}'.format(beter.balance)))
            return
    
        set_to_bet.bets.append(Bet(beter, prediction, amount)) # Add the bet to the set
        set_to_bet.total_bets += amount
        beter.balance -= amount
        print('User %s placed a %s Jipeso bet on %s\s set vs. %s' %(ctx.author.id, '{:.2f}'.format(amount), prediction.name, opponent.name))
        await ctx.channel.send('<@!%s> bet on %s beating %s [-%s%s]' % (ctx.author.id,
                                                                        prediction.get_player_string(),
                                                                        opponent.get_player_string(),
                                                                        bot.jipeso_text,
                                                                        '{:.2f}'.format(amount)) +
                               '\nTotal Sidebets: [%s%s]' % (bot.jipeso_text, '{:.2f}'.format(set_to_bet.total_bets)))
    else:
        await ctx.channel.send('<@!%s> You already placed a bet on this set' % (ctx.author.id))
    save_jipeso_user_json()
    
@commands.command()
async def balance(ctx):
    await ctx.channel.send('<@!%s>\'s Balance: [%s%s]' % (ctx.author.id, bot.jipeso_text, '{:.2f}'.format(get_jipeso_user_from_discord_id(ctx.author.id).balance)))

@commands.command()
async def balanceall(ctx):
    rank = 0
    output_text = ''
    last_balance = -1
    for user in get_sorted_users():
        # Only increase the rank if a new balance is found (tie equal balances)
        if user.balance != last_balance:
            rank += 1
            last_balance = user.balance

        # Add the text to the output
        output_text += str(rank) + '. ' + user.get_mention() + (' [%s%s]' % (bot.jipeso_text, '{:.2f}'.format(user.balance))) + '\n'
        
    await ctx.channel.send(output_text)

@commands.command()
async def linkgg(ctx, gg_id_slug):
    # Get the SmashGG ID from the slug
    gg_id = str(smashsetfunctions.get_gg_id(gg_id_slug, bot.smashgg_key))

    # SmashGG not found
    if gg_id == None:
        await ctx.channel.send('<@!%s> Couldn\'t find account to link to' % ctx.author.id)
        return

    # Link the account if possible
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
    if bot.phase_group_id != None:
        await ctx.channel.send('There\'s already an active tournament')
        return
    
    if ctx.message.author.guild_permissions.administrator == False:
        return
    
    phase_group_json, bot.bracket_link = smashsetfunctions.get_event_standings(tourney_id, bot.smashgg_key)
    if(phase_group_json == None):
        await ctx.channel.send('Tournament not found')
        return

    # Get the tournament information
    bot.phase_group_id = tourney_id
    tourney_name = phase_group_json['phase']['event']['tournament']['name']
    event_name = phase_group_json['phase']['event']['name']

    print('Started Tournament: ' + tourney_name + ' | ' + event_name)
    await ctx.channel.send('Started Tournament: ' + tourney_name + ' | ' + event_name + '\n' + bot.bracket_link)
    
@commands.command()
async def stoptourney(ctx):
    if bot.phase_group_id == None:
        await ctx.channel.send('There\'s no active tournament')
        return
    
    if ctx.message.author.guild_permissions.administrator == False:
        return

    print('Tournament ended')
    await ctx.channel.send('Tournament over')

    # Clear the bracket link and phase group
    bot.bracket_link = ''
    bot.phase_group_id = None

@commands.command()
async def stoptourneyresults(ctx):
    if bot.phase_group_id == None:
        await ctx.channel.send('There\'s no active tournament')
        return
    
    if ctx.message.author.guild_permissions.administrator == False:
        return

    await pay_results(ctx.channel)

    # Clear the bracket link and phase group
    bot.bracket_link = ''
    bot.phase_group_id = None

async def pay_results(message_channel):
    # Get the JSON info
    phase_group_json, bot.bracket_link = smashsetfunctions.get_event_standings(bot.phase_group_id, bot.smashgg_key)
    event_json = phase_group_json['phase']['event']
    results_json = phase_group_json['standings']['nodes']

    # Get the tournament information
    tourney_name = event_json['tournament']['name']
    event_name = event_json['name']
    total_entrants = event_json['numEntrants']
    total_pot = total_entrants * 150
    
    output_string = tourney_name + ' | ' + event_name + ' | Total Entrants: ' + str(total_entrants) + ' | Total Pot: [' + str(bot.jipeso_text) + str(total_pot) + ']\n'
    for result in results_json:
        # Get the placement
        placement = str(result['placement'])

        # Create a Player object
        result_player = Player(result['entrant']['participants'][0]['player']['gamerTag'], str(result['entrant']['participants'][0]['player']['id']), '')
        output_string += placement + '. ' + result_player.get_player_string()

        # Calculate the payout for this placement
        payout_percent = 0
        if placement in payouts:
            payout_percent = float(payouts[placement])
        total_payout = total_pot * (payout_percent/100)
        total_payout = round(total_payout, 2)
        
        # Output the payout if the competitor has a linked Discord
        result_jipeso_user = get_jipeso_user_from_gg_id(result_player.gg_id)
        if result_jipeso_user != None and total_payout != 0:
            result_jipeso_user.balance += total_payout
            output_string += ' [+%s%s]' % (bot.jipeso_text, '{:.2f'.format(total_payout))
            print('Payed out User %s Jipesos to %s for ranking %s in the tournament' % ('{:.2f}'.format(total_payout), result_jipeso_user.discord_id, placement))

        output_string += '\n'

    save_jipeso_user_json()
    await message_channel.send(output_string)

@commands.command()
async def bracket(ctx):
    if bot.bracket_link == '':
        await ctx.channel.send('<@!%s> There\'s no active tournament' % ctx.author.id)
        return

    await ctx.channel.send('<@!%s> %s' % (ctx.author.id, bot.bracket_link))

@commands.command()
async def pay(ctx, reciever_id, amount):
    # Get the IDs
    payer_id = str(ctx.author.id)
    reciever_id = str(reciever_id)
    reciever_id = reciever_id.replace('<', '')
    reciever_id = reciever_id.replace('@', '')
    reciever_id = reciever_id.replace('!', '')
    reciever_id = reciever_id.replace('>', '')

    # Ensure the amount is positive
    amount = amount.replace('-','')
    amount = float(amount)
    amount = round(amount, 2)
        
    try:
        await bot.fetch_user(reciever_id)
    except:
        await ctx.channel.send('<@!%s> Member not found' % (payer_id))
        return

    payer = get_jipeso_user_from_discord_id(payer_id)
    reciever = get_jipeso_user_from_discord_id(reciever_id)

    if payer.balance < amount:
        await ctx.channel.send('<@!%s> Payment is more than your balance [%s%s]' % (ctx.author.id, bot.jipeso_text, '{:.2f}'.format(payer.balance)))
    
    payer.balance -= amount
    reciever.balance += amount

    print('User %s paid User %s %s Jipesos' % (payer_id, reciever_id, '{:.2f}'.format(amount)))
    await ctx.channel.send('<@!%s> paid <@!%s> [-%s%s]' % (payer_id, reciever_id, bot.jipeso_text, '{:.2f}'.format(amount)))
    save_jipeso_user_json()

@tasks.loop(seconds=5.0)
async def update_sets():
    # Poll SmashGG
    if bot.phase_group_id != None:
        smashsetfunctions.update_sets(bot.smash_sets, bot.smashgg_key, bot.phase_group_id)

    # Get the bets channel
    bets_channel = bot.get_channel(int(bets_channel_id))

    for smash_set_key in bot.smash_sets:
        smash_set = bot.smash_sets[smash_set_key]
        # Start sets that haven't started
        if smash_set.started == False:
            smash_set.startTime = int(datetime.datetime.now().timestamp())
            start_string = '%s vs. %s started' % (smash_set.players[0].get_player_string(), smash_set.players[1].get_player_string())
            print(start_string)
            await bets_channel.send(start_string)
            smash_set.started = True

        # Finish complete sets
        if smash_set.ending == True and smash_set.ended == False:
            bet_text_outputs = smash_set.end(bot.jipeso_text)
            for text_output in bet_text_outputs:
                await bets_channel.send(text_output)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    update_sets.start()
    save_jipeso_user_json_loop.start()
    bot.jipeso_text = discord.utils.get(bot.emojis, name='jipeso')

bot.add_command(challenge)
bot.add_command(accept)
bot.add_command(decline)
bot.add_command(reportwin)

bot.add_command(bet)
bot.add_command(balance)
bot.add_command(balanceall)
bot.add_command(starttourney)
bot.add_command(stoptourney)
bot.add_command(stoptourneyresults)
bot.add_command(bracket)
bot.add_command(linkgg)
bot.add_command(pay)
bot.run(discord_key)
