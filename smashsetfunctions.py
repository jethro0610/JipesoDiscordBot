import requests
import json
from jipesoclasses import SmashSet
from jipesoclasses import Player

def get_event_standings(phase_group_id, smashgg_key):
    url = 'https://api.smash.gg/gql/alpha'
    query = """
            {
                phaseGroup(id: "%s"){
                    id
                    standings {
                        nodes {
                            placement
                            entrant{
                                participants {
                                    player {
                                        id
                                        gamerTag
                                    }
                                }
                            }
                        }
                    }
                    phase {
                        id
                        event {
                            slug
                            name
                            numEntrants
                            tournament {
                                name
                            }
                        }
                    }
                }
            }
            """ % phase_group_id
    json = {'query' : query }
    headers = {'Authorization' : 'Bearer %s' % smashgg_key}
    output = requests.post(url, json = json, headers = headers)
    
    if output.json()['data']['phaseGroup'] == None:
        return None, None

    # Construct the bracket link
    event_slug = output.json()['data']['phaseGroup']['phase']['event']['slug']
    url_phase_id = str(output.json()['data']['phaseGroup']['phase']['id'])
    url_phase_group_id = str(output.json()['data']['phaseGroup']['id'])
    bracket_link = 'https://smash.gg/' + event_slug + '/brackets/' + url_phase_id + '/' + url_phase_group_id
    
    return output.json()['data']['phaseGroup'], bracket_link
    
def get_gg_id(gg_id_slug, smashgg_key):
    url = 'https://api.smash.gg/gql/alpha'
    query = """
            {
                user(slug: "user/%s"){
                    player {
                        id
                    }
                }
            }
            """ % gg_id_slug
    json = {'query' : query }
    headers = {'Authorization' : 'Bearer %s' % smashgg_key}
    output = requests.post(url, json = json, headers = headers)
    if output.json()['data']['user'] != None:
        return output.json()['data']['user']['player']['id']
    else:
        return None

def update_sets(smash_sets, smashgg_key, phase_group_id):
    url = 'https://api.smash.gg/gql/alpha'
    query = """
            {
                phaseGroup(id: "%s"){
                    sets {
                        nodes {
                            id
                            startedAt
                            winnerId
                            slots {
                                entrant {
                                    id
                                    participants {
                                        player {
                                            id
                                            gamerTag
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """ % phase_group_id
    json = {'query' : query }
    headers = {'Authorization' : 'Bearer %s' % smashgg_key}
    output = requests.post(url, json = json, headers = headers)
    json_sets = output.json()['data']['phaseGroup']['sets']['nodes']
    
    if json_sets == None:
        return
    
    for json_set in json_sets:
        if json_set['startedAt'] != None: # Add only if the set starrted
            new_smash_set = None
            
            if(json_set['id'] in smash_sets): # Use set the already exists
                new_smash_set = smash_sets[json_set['id']]
            else: # Create a new set if it doesn't exist
                new_smash_set = SmashSet()
                for slot in json_set['slots']:
                    name = slot['entrant']['participants'][0]['player']['gamerTag']
                    gg_id = str(slot['entrant']['participants'][0]['player']['id'])
                    set_id = str(slot['entrant']['id'])
                    new_smash_set.players.append(Player(name, gg_id, set_id))

            # Queue the set to end if there's a winner
            if json_set['winnerId'] != None:
                if not json_set['id'] in smash_sets:
                    new_smash_set.ended = True
                    new_smash_set.started = True
                    
                new_smash_set.ending = True
                new_smash_set.winner_set_id = str(json_set['winnerId'])

            # Assign the set
            smash_sets[json_set['id']] = new_smash_set
