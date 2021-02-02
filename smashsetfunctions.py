import requests
import json
from jipesoclasses import SmashSet

def update_sets(smashSets, smashggKey, eventId):
    url = 'https://api.smash.gg/gql/alpha'
    query = """
            {
                event(id: "%s"){
                    sets {
                        nodes {
                            id
                            startedAt
                            winnerId
                            slots {
                                entrant {
                                    id
                                    name
                                }
                            }
                        }
                    }
                }
            }
            """ % eventId
    json = {'query' : query }
    headers = {'Authorization' : 'Bearer %s' % smashggKey}
    output = requests.post(url, json = json, headers = headers)
    jsonSets = output.json()['data']['event']['sets']['nodes']

    for jsonSet in jsonSets:
        if jsonSet['startedAt'] != None:
            newSmashSet = SmashSet()
            for slot in jsonSet['slots']:
                newSmashSet.players[slot['entrant']['id']] = slot['entrant']['name']

            newSmashSet.startTime = jsonSet['startedAt']

            if jsonSet['winnerId'] != None:
                if not jsonSet['id'] in smashSets:
                    newSmashSet.ended = False
                    newSmashSet.started = False
                    
                newSmashSet.ending = True
                newSmashSet.winner = jsonSet['winnerId']
                   
            smashSets[jsonSet['id']] = newSmashSet
