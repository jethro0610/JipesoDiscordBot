class Player:
    def __init__(self, name, id):
        self.name = name
        self.id = id

class Set:
    def __init__(self, player1, player2):
        self.active = False
        self.player1 = player1
        self.player2 = player2
