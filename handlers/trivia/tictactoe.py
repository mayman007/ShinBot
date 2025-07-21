import random
import time
from pyrogram import Client, types
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import FloodWait
from utils.usage import save_usage

active_ttt_games = {}  # message_id -> game_data
ttt_user_cooldowns = {}  # user_id -> timestamp

# TicTacToe constants
EMPTY = "⬜"
PLAYER_X = "❌"
PLAYER_O = "⭕"

def create_tictactoe_board():
    """Create an empty 3x3 TicTacToe board."""
    return [[EMPTY for _ in range(3)] for _ in range(3)]

def format_board(board):
    """Format the board for display."""
    result = ""
    for row in board:
        result += "".join(row) + "\n"
    return result

def create_board_keyboard(board, game_active=True):
    """Create inline keyboard for the TicTacToe board."""
    keyboard = []
    for i in range(3):
        row = []
        for j in range(3):
            if board[i][j] == EMPTY and game_active:
                row.append(InlineKeyboardButton(" ", callback_data=f"ttt_{i}_{j}"))
            else:
                row.append(InlineKeyboardButton(board[i][j], callback_data=f"ttt_occupied_{i}_{j}"))
        keyboard.append(row)
    
    if not game_active:
        keyboard.append([InlineKeyboardButton("🔄 Play Again", callback_data="ttt_play_again")])
    
    return InlineKeyboardMarkup(keyboard)

def check_winner(board):
    """Check if there's a winner. Returns 'X', 'O', 'tie', or None."""
    # Check rows
    for row in board:
        if row[0] == row[1] == row[2] != EMPTY:
            return row[0]
    
    # Check columns
    for col in range(3):
        if board[0][col] == board[1][col] == board[2][col] != EMPTY:
            return board[0][col]
    
    # Check diagonals
    if board[0][0] == board[1][1] == board[2][2] != EMPTY:
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] != EMPTY:
        return board[0][2]
    
    # Check for tie
    if all(board[i][j] != EMPTY for i in range(3) for j in range(3)):
        return 'tie'
    
    return None

def get_bot_move(board, difficulty='medium'):
    """Get bot move based on difficulty."""
    if difficulty == 'easy':
        return get_random_move(board)
    elif difficulty == 'hard':
        return get_best_move(board)
    else:  # medium
        # 70% chance to play optimally, 30% random
        if random.random() < 0.7:
            return get_best_move(board)
        else:
            return get_random_move(board)

def get_random_move(board):
    """Get a random valid move."""
    empty_cells = [(i, j) for i in range(3) for j in range(3) if board[i][j] == EMPTY]
    return random.choice(empty_cells) if empty_cells else None

def get_best_move(board):
    """Get the best move using minimax algorithm."""
    best_score = -float('inf')
    best_move = None
    
    for i in range(3):
        for j in range(3):
            if board[i][j] == EMPTY:
                board[i][j] = PLAYER_O  # Bot is O
                score = minimax(board, 0, False)
                board[i][j] = EMPTY
                
                if score > best_score:
                    best_score = score
                    best_move = (i, j)
    
    return best_move

def minimax(board, depth, is_maximizing):
    """Minimax algorithm for optimal play."""
    winner = check_winner(board)
    
    if winner == PLAYER_O:  # Bot wins
        return 1
    elif winner == PLAYER_X:  # Player wins
        return -1
    elif winner == 'tie':
        return 0
    
    if is_maximizing:
        best_score = -float('inf')
        for i in range(3):
            for j in range(3):
                if board[i][j] == EMPTY:
                    board[i][j] = PLAYER_O
                    score = minimax(board, depth + 1, False)
                    board[i][j] = EMPTY
                    best_score = max(score, best_score)
        return best_score
    else:
        best_score = float('inf')
        for i in range(3):
            for j in range(3):
                if board[i][j] == EMPTY:
                    board[i][j] = PLAYER_X
                    score = minimax(board, depth + 1, True)
                    board[i][j] = EMPTY
                    best_score = min(score, best_score)
        return best_score

async def tictactoe_command(client: Client, message: types.Message):
    """Handle /tictactoe command."""
    chat = message.chat
    await save_usage(chat, "tictactoe")
    
    # Check cooldown
    user_id = message.from_user.id
    current_time = time.time()
    
    if user_id in ttt_user_cooldowns:
        time_passed = current_time - ttt_user_cooldowns[user_id]
        if time_passed < 5:  # 5 second cooldown
            remaining = int(5 - time_passed)
            await message.reply(f"Please wait {remaining} seconds before starting a new game.")
            return
    
    ttt_user_cooldowns[user_id] = current_time
    
    # Parse arguments
    args = message.text.split()[1:]
    opponent = None
    difficulty = 'medium'
    
    # Check for difficulty setting
    if args and args[-1].lower() in ['easy', 'medium', 'hard']:
        difficulty = args[-1].lower()
        args = args[:-1]
    
    if message.reply_to_message and message.reply_to_message.from_user:
        opponent = message.reply_to_message.from_user
    elif args:
        try:
            if args[0].startswith('@'):
                await message.reply("Please reply to a user's message to challenge them, or play against the bot.")
                return
            else:
                user_id_arg = int(args[0])
                try:
                    opponent = await client.get_users(user_id_arg)
                except Exception:
                    await message.reply("User not found. Please reply to a user's message to challenge them.")
                    return
        except ValueError:
            await message.reply("Invalid user ID. Please reply to a user's message to challenge them.")
            return
    
    # Validate opponent
    if opponent:
        if opponent.id == message.from_user.id:
            await message.reply("You can't play against yourself! 😄")
            return
        elif opponent.is_bot and opponent.id != (await client.get_me()).id:
            await message.reply("You can play with me or with another member. Not another bot!")
            return
    
    # Create initial board
    board = create_tictactoe_board()
    
    if opponent and not opponent.is_bot:
        # Player vs Player
        game_data = {
            "type": "pvp",
            "board": board,
            "player1": message.from_user,  # X
            "player2": opponent,          # O
            "current_turn": "player1",
            "start_time": current_time,
            "player1_wins": 0,
            "player2_wins": 0,
            "ties": 0
        }
        
        text = f"🎯 **TicTacToe**\n\n{message.from_user.first_name} ({PLAYER_X}) vs {opponent.first_name} ({PLAYER_O})\n\nWaiting for **{message.from_user.first_name}** to make a move...\n\n{format_board(board)}"
    else:
        # Player vs Bot
        game_data = {
            "type": "pve",
            "board": board,
            "player1": message.from_user,  # X (player always goes first)
            "current_turn": "player1",
            "difficulty": difficulty,
            "start_time": current_time,
            "player_wins": 0,
            "bot_wins": 0,
            "ties": 0
        }
        
        difficulty_emoji = {"easy": "😊", "medium": "😐", "hard": "😈"}
        # Add difficulty notice if user didn't specify one
        difficulty_notice = ""
        if not any(arg.lower() in ['easy', 'medium', 'hard'] for arg in message.text.split()[1:]):
            difficulty_notice = "\n💡 **Tip: Use `/tictactoe easy`, `/tictactoe medium`, or `/tictactoe hard` to set difficulty**"
        
        text = f"🎯 **TicTacToe**\n\nYou ({PLAYER_X}) vs Bot ({PLAYER_O})\nDifficulty: {difficulty.title()} {difficulty_emoji[difficulty]}\n\nYour turn! Click on an empty cell.\n\n{format_board(board)}{difficulty_notice}"
    
    keyboard = create_board_keyboard(board)
    sent_message = await message.reply(text, reply_markup=keyboard)
    active_ttt_games[sent_message.id] = game_data

async def tictactoe_callback_handler(client: Client, callback_query):
    """Handle TicTacToe button clicks."""
    if not callback_query.data.startswith("ttt_"):
        return
    
    # Handle play again specifically
    if callback_query.data == "ttt_play_again":
        await ttt_play_again_callback(client, callback_query)
        return
    
    # Handle occupied cells
    if "occupied" in callback_query.data:
        await callback_query.answer("This cell is already taken!", show_alert=True)
        return
    
    await callback_query.answer()
    
    message_id = callback_query.message.id
    if message_id not in active_ttt_games:
        await callback_query.message.edit_text("❌ This game has expired. Use /tictactoe to start a new game.")
        return
    
    game_data = active_ttt_games[message_id]
    user = callback_query.from_user
    
    # Check if game has timed out (5 minutes)
    if time.time() - game_data["start_time"] > 300:
        del active_ttt_games[message_id]
        await callback_query.message.edit_text("⏰ Game timed out. Use /tictactoe to start a new game.")
        return
    
    # Parse move
    try:
        _, row, col = callback_query.data.split("_")
        row, col = int(row), int(col)
    except:
        await callback_query.answer("Invalid move!", show_alert=True)
        return
    
    # Validate move
    if game_data["board"][row][col] != EMPTY:
        await callback_query.answer("This cell is already taken!", show_alert=True)
        return
    
    if game_data["type"] == "pve":
        # Player vs Bot
        if user.id != game_data["player1"].id:
            await callback_query.answer("This is not your game!", show_alert=True)
            return
        
        if game_data["current_turn"] != "player1":
            await callback_query.answer("Wait for the bot to make its move!", show_alert=True)
            return
        
        # Player move
        game_data["board"][row][col] = PLAYER_X
        
        # Check for winner after player move
        winner = check_winner(game_data["board"])
        if winner:
            await handle_game_end(callback_query, game_data, winner)
            return
        
        # Bot's turn
        game_data["current_turn"] = "bot"
        bot_move = get_bot_move(game_data["board"], game_data["difficulty"])
        
        if bot_move:
            bot_row, bot_col = bot_move
            game_data["board"][bot_row][bot_col] = PLAYER_O
            
            # Check for winner after bot move
            winner = check_winner(game_data["board"])
            if winner:
                await handle_game_end(callback_query, game_data, winner)
                return
        
        game_data["current_turn"] = "player1"
        
        # Update display
        difficulty_emoji = {"easy": "😊", "medium": "😐", "hard": "😈"}
        text = f"🎯 **TicTacToe**\n\nYou ({PLAYER_X}) vs Bot ({PLAYER_O})\nDifficulty: {game_data['difficulty'].title()} {difficulty_emoji[game_data['difficulty']]}\n\nYour turn! Click on an empty cell.\n\n{format_board(game_data['board'])}"
        
        keyboard = create_board_keyboard(game_data["board"])
        
        try:
            await callback_query.message.edit_text(text, reply_markup=keyboard)
        except FloodWait as e:
            await callback_query.answer(f"Please wait {e.value} seconds before making another move due to rate limits.", show_alert=True)
            return
        except Exception as e:
            await callback_query.answer(f"Error updating game: {str(e)}", show_alert=True)
    
    else:
        # Player vs Player
        if user.id == game_data["player1"].id and game_data["current_turn"] == "player1":
            game_data["board"][row][col] = PLAYER_X
            game_data["current_turn"] = "player2"
            current_player = game_data["player2"].first_name
        elif user.id == game_data["player2"].id and game_data["current_turn"] == "player2":
            game_data["board"][row][col] = PLAYER_O
            game_data["current_turn"] = "player1"
            current_player = game_data["player1"].first_name
        else:
            await callback_query.answer("It's not your turn!", show_alert=True)
            return
        
        # Check for winner
        winner = check_winner(game_data["board"])
        if winner:
            await handle_game_end(callback_query, game_data, winner)
            return
        
        # Update display
        text = f"🎯 **TicTacToe**\n\n{game_data['player1'].first_name} ({PLAYER_X}) vs {game_data['player2'].first_name} ({PLAYER_O})\n\nWaiting for **{current_player}** to make a move...\n\n{format_board(game_data['board'])}"
        
        keyboard = create_board_keyboard(game_data["board"])
        
        try:
            await callback_query.message.edit_text(text, reply_markup=keyboard)
        except FloodWait as e:
            await callback_query.answer(f"Please wait {e.value} seconds before making another move due to rate limits.", show_alert=True)
            return
        except Exception as e:
            await callback_query.answer(f"Error updating game: {str(e)}", show_alert=True)

async def handle_game_end(callback_query, game_data, winner):
    """Handle end of game logic."""
    message_id = callback_query.message.id
    
    if winner == 'tie':
        result_text = "It's a tie! 🤝"
        game_data["ties"] += 1
    elif game_data["type"] == "pve":
        if winner == PLAYER_X:
            result_text = "You won! 🎉"
            game_data["player_wins"] += 1
        else:
            result_text = "Bot wins! 🤖"
            game_data["bot_wins"] += 1
    else:  # pvp
        if winner == PLAYER_X:
            result_text = f"**{game_data['player1'].first_name}** wins! 🎉"
            game_data["player1_wins"] += 1
        else:
            result_text = f"**{game_data['player2'].first_name}** wins! 🎉"
            game_data["player2_wins"] += 1
    
    # Create final display
    if game_data["type"] == "pve":
        score_text = f"\n\n📊 **Score:**\nYou: {game_data['player_wins']} | Bot: {game_data['bot_wins']} | Ties: {game_data['ties']}"
        difficulty_emoji = {"easy": "😊", "medium": "😐", "hard": "😈"}
        final_text = f"🎯 **Game Over**\n\n{result_text}\n\nYou ({PLAYER_X}) vs Bot ({PLAYER_O})\nDifficulty: {game_data['difficulty'].title()} {difficulty_emoji[game_data['difficulty']]}\n\n{format_board(game_data['board'])}{score_text}"
    else:
        score_text = f"\n\n📊 **Score:**\n{game_data['player1'].first_name}: {game_data['player1_wins']} | {game_data['player2'].first_name}: {game_data['player2_wins']} | Ties: {game_data['ties']}"
        final_text = f"🎯 **Game Over**\n\n{result_text}\n\n{game_data['player1'].first_name} ({PLAYER_X}) vs {game_data['player2'].first_name} ({PLAYER_O})\n\n{format_board(game_data['board'])}{score_text}"
    
    keyboard = create_board_keyboard(game_data["board"], game_active=False)
    
    try:
        await callback_query.message.edit_text(final_text, reply_markup=keyboard)
    except FloodWait as e:
        await callback_query.answer(f"Please wait {e.value} seconds due to rate limits. Game will end automatically.", show_alert=True)
        return
    except Exception as e:
        await callback_query.answer(f"Error ending game: {str(e)}", show_alert=True)
        return
    
    # Store game result for play again
    active_ttt_games[message_id] = {
        "type": "result",
        "original_type": game_data["type"],
        "player1": game_data["player1"],
        "player2": game_data.get("player2"),
        "difficulty": game_data.get("difficulty", "medium"),
        "start_time": time.time(),
        "player1_wins": game_data.get("player1_wins", 0),
        "player2_wins": game_data.get("player2_wins", 0),
        "player_wins": game_data.get("player_wins", 0),
        "bot_wins": game_data.get("bot_wins", 0),
        "ties": game_data.get("ties", 0)
    }

async def ttt_play_again_callback(client: Client, callback_query):
    """Handle play again button for TicTacToe."""
    await callback_query.answer()
    
    message_id = callback_query.message.id
    if message_id not in active_ttt_games:
        await callback_query.message.edit_text("❌ This game has expired. Use /tictactoe to start a new game.")
        return
    
    game_data = active_ttt_games[message_id]
    user = callback_query.from_user
    
    # Check if user is part of the game
    is_player1 = user.id == game_data["player1"].id
    is_player2 = "player2" in game_data and game_data["player2"] and user.id == game_data["player2"].id
    
    if not (is_player1 or is_player2):
        await callback_query.answer("You're not part of this game!", show_alert=True)
        return
    
    current_time = time.time()
    if current_time - game_data["start_time"] < 1:
        await callback_query.answer("Please wait a moment before starting a new game.", show_alert=True)
        return
    
    # For PvP games, require both players to agree
    if game_data.get("original_type") == "pvp" and game_data.get("player2"):
        if "play_again_votes" not in game_data:
            game_data["play_again_votes"] = {}
        
        if user.id in game_data["play_again_votes"]:
            await callback_query.answer("You already pressed play again! Waiting for the other player.", show_alert=True)
            return
        
        game_data["play_again_votes"][user.id] = {"name": user.first_name, "time": current_time}
        
        if len(game_data["play_again_votes"]) == 1:
            first_voter = list(game_data["play_again_votes"].values())[0]["name"]
            other_player = game_data["player2"].first_name if is_player1 else game_data["player1"].first_name
            
            current_text = callback_query.message.text
            waiting_text = f"{current_text}\n\n⏳ **{first_voter}** wants to play again!\nWaiting for **{other_player}** to agree..."
            
            keyboard = create_board_keyboard([[EMPTY for _ in range(3)] for _ in range(3)], game_active=False)
            
            try:
                await callback_query.message.edit_text(waiting_text, reply_markup=keyboard)
            except FloodWait as e:
                await callback_query.answer(f"Please wait {e.value} seconds due to rate limits.", show_alert=True)
                return
            except Exception as e:
                await callback_query.answer(f"Error updating game: {str(e)}", show_alert=True)
            return
    
    # Start new game
    board = create_tictactoe_board()
    new_start_time = current_time
    
    if game_data.get("original_type") == "pvp" and game_data.get("player2"):
        # Player vs Player rematch
        new_game_data = {
            "type": "pvp",
            "board": board,
            "player1": game_data["player1"],
            "player2": game_data["player2"],
            "current_turn": "player1",
            "start_time": new_start_time,
            "player1_wins": game_data.get("player1_wins", 0),
            "player2_wins": game_data.get("player2_wins", 0),
            "ties": game_data.get("ties", 0)
        }
        
        score_text = f"\n\n📊 **Current Score:**\n{game_data['player1'].first_name}: {game_data.get('player1_wins', 0)} | {game_data['player2'].first_name}: {game_data.get('player2_wins', 0)} | Ties: {game_data.get('ties', 0)}"
        text = f"🎯 **TicTacToe**\n\n{game_data['player1'].first_name} ({PLAYER_X}) vs {game_data['player2'].first_name} ({PLAYER_O})\n\nWaiting for **{game_data['player1'].first_name}** to make a move...\n\n{format_board(board)}{score_text}"
    else:
        # Player vs Bot rematch
        if not is_player1:
            await callback_query.answer("Only the original player can start a new game!", show_alert=True)
            return
        
        new_game_data = {
            "type": "pve",
            "board": board,
            "player1": game_data["player1"],
            "current_turn": "player1",
            "difficulty": game_data.get("difficulty", "medium"),
            "start_time": new_start_time,
            "player_wins": game_data.get("player_wins", 0),
            "bot_wins": game_data.get("bot_wins", 0),
            "ties": game_data.get("ties", 0)
        }
        
        difficulty_emoji = {"easy": "😊", "medium": "😐", "hard": "😈"}
        score_text = f"\n\n📊 **Current Score:**\nYou: {game_data.get('player_wins', 0)} | Bot: {game_data.get('bot_wins', 0)} | Ties: {game_data.get('ties', 0)}"
        text = f"🎯 **TicTacToe**\n\nYou ({PLAYER_X}) vs Bot ({PLAYER_O})\nDifficulty: {game_data['difficulty'].title()} {difficulty_emoji[game_data['difficulty']]}\n\nYour turn! Click on an empty cell.\n\n{format_board(board)}{score_text}"
    
    keyboard = create_board_keyboard(board)
    active_ttt_games[message_id] = new_game_data
    
    try:
        await callback_query.message.edit_text(text, reply_markup=keyboard)
    except FloodWait as e:
        await callback_query.answer(f"Please wait {e.value} seconds before starting a new game due to rate limits.", show_alert=True)
        return
    except Exception as e:
        await callback_query.answer(f"Error starting new game: {str(e)}", show_alert=True)
