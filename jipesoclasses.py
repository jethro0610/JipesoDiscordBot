class SmashSet:
    def __init__(self):
        self.players = dict()
        self.bets = dict()
        self.startTime = 0
        self.started = False
        self.winner = None
        self.ending = False
        self.ended = False

class Bet:
    def __init__(self, predictionId, amount):
        self.predictionId = predictionId
        self.amount = amount
