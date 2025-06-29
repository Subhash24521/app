from fastapi import APIRouter, Depends, HTTPException, Form
from app.core.deps import get_current_user_from_cookie
from app.games.ludo.game_manager import game_manager

router = APIRouter()

@router.post("/games/ludo/{room_id}/start")
def start_ludo(room_id: int, user=Depends(get_current_user_from_cookie)):
    game = game_manager.create_game(room_id)
    game.add_player(user.id, "red")  # You can assign colors dynamically
    game.start_game()
    return {"message": "Game started"}

@router.post("/games/ludo/{room_id}/roll")
def roll_dice(room_id: int, user=Depends(get_current_user_from_cookie)):
    game = game_manager.get_game(room_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if user.id != game.get_current_turn():
        raise HTTPException(status_code=403, detail="Not your turn")
    value = game.roll_dice()
    return {"dice": value}

@router.post("/games/ludo/{room_id}/move")
def move_piece(room_id: int, piece_index: int = Form(...), dice_value: int = Form(...), user=Depends(get_current_user_from_cookie)):
    game = game_manager.get_game(room_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    game.move_piece(user.id, piece_index, dice_value)
    return {"message": "Piece moved"}
