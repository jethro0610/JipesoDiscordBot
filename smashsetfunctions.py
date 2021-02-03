import requests
import json
from jipesoclasses import SmashSet

def get_event_standings(phaseGroupId, smashggKey):
    url = 'https://api.smash.gg/gql/alpha'
    query = """
            {
                phaseGroup(id: "%s"){
                    id
                    phase {
                        id
                        event {
                            slug
                            name
                            numEntrants
                            tournament {
                                name
                            }
                            standings(query: {
                                perPage: 16
                                page: 1
                            }){
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
                        }
                    }
                }
            }
            """ % phaseGroupId
    json = {'query' : query }
    headers = {'Authorization' : 'Bearer %s' % smashggKey}
    output = requests.post(url, json = json, headers = headers)

    eventSlug = output.json()['data']['phaseGroup']['phase']['event']['slug']
    urlPhaseId = str(output.json()['data']['phaseGroup']['phase']['id'])
    urlPhaseGroupId = str(output.json()['data']['phaseGroup']['id'])
    bracketLink = 'https://smash.gg/' + eventSlug + '/brackets/' + urlPhaseId + '/' + urlPhaseGroupId
    
    return output.json()['data']['phaseGroup']['phase']['event'], bracketLink
    
def get_gg_id(ggSlug, smashggKey):
    url = 'https://api.smash.gg/gql/alpha'
    query = """
            {
                user(slug: "user/%s"){
                    player {
                        id
                    }
                }
            }
            """ % ggSlug
    json = {'query' : query }
    headers = {'Authorization' : 'Bearer %s' % smashggKey}
    output = requests.post(url, json = json, headers = headers)
    if output.json()['data']['user'] != None:
        return output.json()['data']['user']['player']['id']
    else:
        return None

def update_sets(smashSets, smashggKey, phaseGroupId):
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
            """ % phaseGroupId
    json = {'query' : query }
    headers = {'Authorization' : 'Bearer %s' % smashggKey}
    output = requests.post(url, json = json, headers = headers)
    jsonSets = output.json()['data']['phaseGroup']['sets']['nodes']
    
    if jsonSets == None:
        return

    for jsonSet in jsonSets:
        if jsonSet['startedAt'] != None:
            newSmashSet = None
            if(jsonSet['id'] in smashSets):
                newSmashSet = smashSets[jsonSet['id']]
            else:
                newSmashSet = SmashSet()
                newSmashSet.startTime = jsonSet['startedAt']
                for slot in jsonSet['slots']:
                    newSmashSet.players[slot['entrant']['id']] = {'name' : slot['entrant']['participants'][0]['player']['gamerTag'],
                                                                  'ggId' : str(slot['entrant']['participants'][0]['player']['id'])}

            if jsonSet['winnerId'] != None:
                if not jsonSet['id'] in smashSets:
                    newSmashSet.ended = True
                    newSmashSet.started = True
                    
                newSmashSet.ending = True
                newSmashSet.winner = jsonSet['winnerId']
                   
            smashSets[jsonSet['id']] = newSmashSet
