import random

class LudoGame:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players = {}  # {user_id: {'pieces': [0, 0, 0, 0], 'color': 'red'}}
        self.turn_order = []
        self.current_turn_index = 0
        self.started = False

    def add_player(self, user_id, color):
        if self.started:
            raise Exception("Game already started")
        self.players[user_id] = {"pieces": [0, 0, 0, 0], "color": color}
        self.turn_order.append(user_id)

    def start_game(self):
        self.started = True
        self.current_turn_index = 0

    def roll_dice(self):
        return random.randint(1, 6)

    def get_current_turn(self):
        return self.turn_order[self.current_turn_index]

    def next_turn(self):
        self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)

    def move_piece(self, user_id, piece_index, dice_value):
        if user_id != self.get_current_turn():
            raise Exception("Not your turn")
        self.players[user_id]['pieces'][piece_index] += dice_value
        self.next_turn()
