import os
import discord
import requests
import json
import jipesoclasses

with open("config.json") as json_data_file:
    config = json.load(json_data_file)

smashggKey = config['smashggKey']
eventId = config['eventId']
discordKey = config['discordKey']
    
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

client = discord.Client()

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

client.run(discordKey)
