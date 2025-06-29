# app/games/ludo/game_manager.py

from app.games.ludo.logic import LudoGame

class LudoGameManager:
    def __init__(self):
        self.active_games = {}  # room_id -> LudoGame

    def get_game(self, room_id):
        return self.active_games.get(room_id)

    def create_game(self, room_id):
        game = LudoGame(room_id)
        self.active_games[room_id] = game
        return game

game_manager = LudoGameManager()
