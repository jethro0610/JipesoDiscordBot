import json

jipeso_users = []
jipeso_user_dict = dict()
gg_id_to_jipeso_user_dict = dict()
losers_pay = 0
winners_pay = 0

def set_winners_pay(new_pay):
    global winners_pay
    winners_pay = round(new_pay, 2)

def set_losers_pay(new_pay):
    global losers_pay
    losers_pay = round(new_pay, 2)

def gg_id_to_discord_id(gg_id):
    global gg_id_to_jipeso_user_dict
    return gg_id_to_jipeso_user_dict[gg_id]

def discord_id_to_gg_id(discord_id):
    discord_id = str(discord_id)
    # Ensure the Discord ID exists
    key_list = list(gg_id_to_jipeso_user_dict.keys())
    val_list = list(gg_id_to_jipeso_user_dict.values())
    if not discord_id in val_list:
        print('no disc_id')
        return None

    return str(key_list[val_list.index(discord_id)])

def mention_to_gg_id(mention):
    global gg_id_to_jipeso_user_dict

    # Remove mention formatting
    mention = mention.replace('<', '')
    mention = mention.replace('@', '')
    mention = mention.replace('!', '')
    mention = mention.replace('>', '')

    return discord_id_to_gg_id(mention)

def create_new_jipeso_user(discord_id):
    global jippi_user_dict
    global jippi_users
    
    new_user = JipesoUser(discord_id, 100) # Create the user object
    jipeso_user_dict[discord_id] = len(jipeso_users) # Assign the dictionary location
    jipeso_users.append(new_user) # Add the user object
    save_jipeso_user_json()

def load_gg_id_json():
    global gg_id_to_jipeso_user_dict
    
    with open('ggIds.json') as json_data_file:
        gg_id_to_jipeso_user_dict = json.load(json_data_file)

def save_gg_id_json():
    global gg_id_to_jipeso_user_dict
    
    with open('ggIds.json', 'w') as json_data_file:
        json.dump(gg_id_to_jipeso_user_dict, json_data_file)

def get_jipeso_user_from_gg_id(gg_id):
    global gg_id_to_jipeso_user_dict
    
    gg_id = str(gg_id)
    if not gg_id in gg_id_to_jipeso_user_dict:
        return None
        
    return get_jipeso_user_from_discord_id(gg_id_to_jipeso_user_dict[gg_id])

def get_jipeso_user_from_discord_id(discord_id):
    global jipeso_user_dict
    global jipeso_users
    
    discord_id = str(discord_id)

    # Create a new Jipeso User if they don't exist
    if not discord_id in jipeso_user_dict:
        create_new_jipeso_user(discord_id)
        
    return jipeso_users[jipeso_user_dict[discord_id]]

def get_jipeso_user_from_mention(mention):
    # Remove mention formatting
    mention = mention.replace('<', '')
    mention = mention.replace('@', '')
    mention = mention.replace('!', '')
    mention = mention.replace('>', '')

    return get_jipeso_user_from_discord_id(mention)

def add_gg_id_to_jipeso_user(gg_id, discord_id):
    global gg_id_to_jipeso_user_dict
    global jipeso_user_dict
    
    gg_id = str(gg_id)
    discord_id = str(discord_id)
    if gg_id in gg_id_to_jipeso_user_dict:
        return -1
    elif discord_id in gg_id_to_jipeso_user_dict.values():
        return 0
    else:
        gg_id_to_jipeso_user_dict[gg_id] = discord_id

        # Create a new Jipeso User if they don't exist
        if not discord_id in jipeso_user_dict:
            create_new_jipeso_user(discord_id)
        
        save_gg_id_json()
        return 1

def load_jipeso_user_json():
    global jipeso_user_dict
    global jipeso_users
    
    with open('jipeso.json') as json_data_file:
        jipeso_json = json.load(json_data_file)

    # Construct a Jipeso User from the JSON
    for json_entry in jipeso_json:
        new_user = JipesoUser(json_entry, jipeso_json[json_entry])
        jipeso_user_dict[json_entry] = len(jipeso_users)
        jipeso_users.append(new_user)

def save_jipeso_user_json():
    global jipeso_users
    
    save_dict = dict()
    for jipeso_user in jipeso_users:
        save_dict[jipeso_user.discord_id] = jipeso_user.balance
        
    with open('jipeso.json', 'w') as json_data_file:
        json.dump(save_dict, json_data_file)
    print("Saved Jipesos file")

class SmashSet:
    def __init__(self):
        self.players = []
        self.bets = []
        self.total_bets = 0.0
        self.start_time = 0
        self.started = False
        self.winner_set_id = None
        self.ending = False
        self.ended = False
        self.wager = -1

    def discord_id_has_bet(self, discord_id):
        for bet in self.bets:
            if bet.beter.discord_id == str(discord_id):
                return True
        return False
    
    def end(self, jipeso_text = 'Jipesos'):
        text_output = []
        winner_bet_amount = 0.0
        winner_int = -1
        loser_int = -1
        counter = 0

        # Get the total amount fof winning bets
        for bet in self.bets:
            if bet.prediction.set_id == self.winner_set_id:
                winner_bet_amount += bet.amount

        # Get the winner
        for player in self.players:
            if player.set_id == self.winner_set_id:
                winner_int = counter
            counter += 1

        # Get the winning and losing Player objects
        loser_int = 1 - winner_int
        losing_player = self.players[loser_int]
        winning_player = self.players[winner_int]
        
        text_output.append('%s won over %s | Total Sidebets: [%s%s]' % (winning_player.get_player_string(), losing_player.get_player_string(), jipeso_text, '{:.2f}'.format(self.total_bets)))

        # Give Jipesos to the winning Jipeso User
        winning_user = winning_player.get_jipeso_user()
        if winning_user != None:
            winning_amount = 0
            if self.wager == -1:
                winning_amount = winners_pay
            else:
                winning_amount = self.wager * 2.0

            winning_user.balance += winning_amount
            print('User %s earned %s Jipesos for winning' % (winning_user.discord_id, '{:.2f}'.format(winning_amount)))
            text_output.append('%s won and earned [+%s%s]' % (winning_player.get_player_string(), jipeso_text, '{:.2f}'.format(winning_amount)))

        # Give Jipesos to the losing Jipeso User
        losing_user = losing_player.get_jipeso_user()
        if losing_user != None and self.wager == -1:
            losing_user.balance += losers_pay
            print('User %s earned %s Jipesos for losing' % (losing_user.discord_id, '{:.2f}'.format(losers_pay)))
            text_output.append('%s tried and got [+%s%s]' % (losing_player.get_player_string(), jipeso_text, '{:.2f}'.format(losers_pay)))

        # Skip if there's no bets
        if winner_bet_amount == 0.0 or self.total_bets == 0.0:
            self.ended = True
            return text_output

        # Award the bets earnings to winners
        for bet in self.bets:
            # Skip if the bet is losing
            if bet.prediction.set_id != self.winner_set_id:
                continue
            
            percent_of_pot = bet.amount / winner_bet_amount
            earnings = self.total_bets * percent_of_pot
            earnings = round(earnings, 2)
            bonus_string = ''
            
            # Double earnings if 80% of pot is bet
            if percent_of_pot >= 0.8:
                earnings *= 2.0
                bonus_string = ' with a 2x bonus '

            bet.beter.balance += earnings
            print('User %s earned %s Jipesos in bettings' % (bet.beter.discord_id, '{:.2f}'.format(earnings)))
            text_output.append(('<@!%s> earned %s%% of the pot' + bonus_string + '[+%s%s]') % (bet.beter.discord_id, '{:.2f}'.format(percent_of_pot * 100), jipeso_text, '{:.2f}'.format(earnings)))

        save_jipeso_user_json()
        self.ended = True
        return text_output
    
class Bet:
    def __init__(self, beter, prediction, amount):
        self.beter = beter
        self.prediction = prediction
        self.amount = amount

class JipesoUser:
    def __init__(self, discord_id, balance):
        self.discord_id = str(discord_id)
        self.balance = float(balance)

    def get_mention(self):
        return '<@!%s>' % self.discord_id
        
class Player:
    def __init__(self, name, gg_id, set_id):
        self.name = name
        self.gg_id = str(gg_id)
        self.set_id = set_id
        self.jipeso_user = get_jipeso_user_from_gg_id(self.gg_id)

    def get_jipeso_user(self):
        return self.jipeso_user
        #return get_jipeso_user_from_gg_id(self.gg_id)
    
    def get_player_string(self):
        if self.get_jipeso_user() != None:
            return self.get_jipeso_user().get_mention()
        else:
            return self.name

def merge_users(left, right):
    merge_array = []

    # Keep sorting until elements run out in one of the arrays
    while len(left) > 0 and len(right) > 0:
        # Place the largest of the first elements of the users in the merged array
        if left[0].balance > right[0].balance:
            merge_array.append(left[0])
            del left[0]
        else:
            merge_array.append(right[0])
            del right[0]

    # Add remaining elements to end of merge array
    while len(left) > 0:
        merge_array.append(left[0])
        del left[0]
        
    while len(right) > 0:
        merge_array.append(right[0])
        del right[0]
        
    return merge_array

def sort_users(users):
    # Return if the array size is 1
    if len(users) == 1:
        return users
    
    # Find the middle of the array
    middle = len(users)//2

    # Split the array into two
    left = users[:middle]
    right = users[middle:]

    # Recursively merge_sort the arrays
    left = sort_users(left)
    right = sort_users(right)

    # Return the merged, sorted array
    return merge_users(left, right)

def get_sorted_users():
    return sort_users(jipeso_users)
        
