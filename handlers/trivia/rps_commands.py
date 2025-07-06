import random
import time
from pyrogram import Client, types
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import FloodWait
from utils.usage import save_usage

# Game data storage (in production, consider using a database)
active_games = {}  # message_id -> game_data
user_cooldowns = {}  # user_id -> timestamp

# Game choices
CHOICES = {
    "rock": {"emoji": "🪨", "beats": "scissors"},
    "paper": {"emoji": "🧻", "beats": "rock"}, 
    "scissors": {"emoji": "✂️", "beats": "paper"}
}

def get_winner(choice1, choice2):
    """Determine winner between two choices. Returns 1 if choice1 wins, 2 if choice2 wins, 0 if tie."""
    if choice1 == choice2:
        return 0  # Tie
    elif CHOICES[choice1]["beats"] == choice2:
        return 1  # Player 1 wins
    else:
        return 2  # Player 2 wins

def format_choice(choice):
    """Format choice with emoji."""
    return f"{choice} {CHOICES[choice]['emoji']}"

async def rps_command(client: Client, message: types.Message):
    """Handle /rps command for Rock Paper Scissors game."""
    chat = message.chat
    await save_usage(chat, "rps")
    
    # Check cooldown
    user_id = message.from_user.id
    current_time = time.time()
    
    if user_id in user_cooldowns:
        time_passed = current_time - user_cooldowns[user_id]
        if time_passed < 5:  # 5 second cooldown
            remaining = int(5 - time_passed)
            await message.reply(f"Please wait {remaining} seconds before starting a new game.")
            return
    
    user_cooldowns[user_id] = current_time
    
    # Parse arguments to check for opponent
    args = message.text.split()[1:]
    opponent = None
    
    if message.reply_to_message and message.reply_to_message.from_user:
        opponent = message.reply_to_message.from_user
    elif args:
        # Try to parse user ID or username from arguments
        try:
            if args[0].startswith('@'):
                username = args[0][1:]
                # In a real implementation, you'd need to resolve username to user
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
            await message.reply("You can't play against yourself! You can play with me if you're that lonely... 😄")
            return
        elif opponent.is_bot and opponent.id != (await client.get_me()).id:
            await message.reply("You can play with me or with another member. Not another bot!")
            return
    
    # Create game buttons
    buttons = [
        [
            InlineKeyboardButton("🪨 Rock", callback_data="rps_rock"),
            InlineKeyboardButton("🧻 Paper", callback_data="rps_paper"),
            InlineKeyboardButton("✂️ Scissors", callback_data="rps_scissors")
        ]
    ]
    
    if opponent and not opponent.is_bot:
        # Player vs Player
        game_data = {
            "type": "pvp",
            "player1": message.from_user,
            "player2": opponent,
            "player1_choice": None,
            "player2_choice": None,
            "current_turn": "player1",
            "start_time": current_time,
            "player1_wins": 0,
            "player2_wins": 0,
            "ties": 0
        }
        
        text = f"🎮 **Rock Paper Scissors**\n\n{message.from_user.first_name} vs {opponent.first_name}\n\nWaiting for **{message.from_user.first_name}** to choose...\n\nRock, paper, or scissors? Choose wisely!"
    else:
        # Player vs Bot
        game_data = {
            "type": "pve",
            "player1": message.from_user,
            "player2": None,
            "player1_choice": None,
            "bot_choice": None,
            "start_time": current_time,
            "player_wins": 0,
            "bot_wins": 0,
            "ties": 0
        }
        
        text = "🎮 **Rock Paper Scissors**\n\nYou vs Bot\n\nRock, paper, or scissors? Choose wisely!"
    
    sent_message = await message.reply(text, reply_markup=InlineKeyboardMarkup(buttons))
    active_games[sent_message.id] = game_data

async def rps_callback_handler(client: Client, callback_query):
    """Handle RPS button clicks."""
    if not callback_query.data.startswith("rps_"):
        return
    
    # Handle play again specifically
    if callback_query.data == "rps_play_again":
        await rps_play_again_callback(client, callback_query)
        return
    
    await callback_query.answer()
    
    message_id = callback_query.message.id
    if message_id not in active_games:
        await callback_query.message.edit_text("❌ This game has expired. Use /rps to start a new game.")
        return
    
    game_data = active_games[message_id]
    user = callback_query.from_user
    choice = callback_query.data.split("_")[1]  # Extract choice from callback_data
    
    # Check if game has timed out (3 minutes)
    if time.time() - game_data["start_time"] > 180:
        del active_games[message_id]
        await callback_query.message.edit_text("⏰ Game timed out. Use /rps to start a new game.")
        return
    
    if game_data["type"] == "pve":
        # Player vs Bot
        if user.id != game_data["player1"].id:
            await callback_query.answer("This is not your game!", show_alert=True)
            return
        
        game_data["player1_choice"] = choice
        bot_choice = random.choice(list(CHOICES.keys()))
        game_data["bot_choice"] = bot_choice
        
        # Determine winner
        result = get_winner(choice, bot_choice)
        
        player_choice_text = format_choice(choice)
        bot_choice_text = format_choice(bot_choice)
        
        if result == 0:
            result_text = "Well, that was weird. We tied."
            emoji = "🤝"
            game_data["ties"] += 1
        elif result == 1:
            if choice == "rock" and bot_choice == "scissors":
                result_text = "Aw, you beat me. It won't happen again!"
            elif choice == "paper" and bot_choice == "rock":
                result_text = "Aw man, you actually managed to beat me."
            else:  # scissors beats paper
                result_text = "Bruh. >: |"
            emoji = "🎉"
            game_data["player_wins"] += 1
        else:
            if bot_choice == "rock" and choice == "scissors":
                result_text = "HAHA!! I JUST CRUSHED YOU!! I rock!!"
            elif bot_choice == "paper" and choice == "rock":
                result_text = "Nice try, but I won this time!!"
            else:  # bot scissors beats player paper
                result_text = "I WON!!!"
            emoji = "🤖"
            game_data["bot_wins"] += 1
        
        # Create play again button
        play_again_button = [[InlineKeyboardButton("🔄 Play Again", callback_data="rps_play_again")]]
        
        # Add score to final text
        score_text = f"\n\n📊 **Score:**\nYou: {game_data['player_wins']} | Bot: {game_data['bot_wins']} | Ties: {game_data['ties']}"
        
        final_text = (f"{emoji} **Game Result**\n\n"
                     f"{result_text}\n\n"
                     f"**Your choice:** {player_choice_text}\n"
                     f"**My choice:** {bot_choice_text}"
                     f"{score_text}")
        
        try:
            await callback_query.message.edit_text(final_text, reply_markup=InlineKeyboardMarkup(play_again_button))
        except FloodWait as e:
            await callback_query.answer(f"Please wait {e.value} seconds before trying again due to rate limits.", show_alert=True)
            return
        except Exception as e:
            await callback_query.answer(f"Error updating game: {str(e)}", show_alert=True)
            return
        
        # Store game result for play again
        active_games[message_id] = {
            "type": "result",
            "player1": game_data["player1"],
            "start_time": time.time(),
            "player_wins": game_data["player_wins"],
            "bot_wins": game_data["bot_wins"],
            "ties": game_data["ties"]
        }
        
    else:
        # Player vs Player
        if user.id == game_data["player1"].id and game_data.get("current_turn") == "player1":
            game_data["player1_choice"] = choice
            game_data["current_turn"] = "player2"
            
            # Update message for player 2's turn
            text = (f"🎮 **Rock Paper Scissors**\n\n"
                   f"{game_data['player1'].first_name} vs {game_data['player2'].first_name}\n\n"
                   f"Waiting for **{game_data['player2'].first_name}** to choose...\n\n"
                   f"Rock, paper, or scissors? Choose wisely!")
            
            try:
                await callback_query.message.edit_text(text, reply_markup=callback_query.message.reply_markup)
            except FloodWait as e:
                await callback_query.answer(f"Please wait {e.value} seconds before trying again due to rate limits.", show_alert=True)
                return
            except Exception as e:
                await callback_query.answer(f"Error updating game: {str(e)}", show_alert=True)
                return

        elif user.id == game_data["player2"].id and game_data.get("current_turn") == "player2":
            game_data["player2_choice"] = choice
            
            # Both players have chosen, determine winner
            player1_choice = game_data["player1_choice"]
            player2_choice = choice
            
            result = get_winner(player1_choice, player2_choice)
            
            player1_choice_text = format_choice(player1_choice)
            player2_choice_text = format_choice(player2_choice)
            
            if result == 0:
                result_text = "Well, that was weird. Both of you tied."
                emoji = "🤝"
                game_data["ties"] += 1
            elif result == 1:
                result_text = f"**{game_data['player1'].first_name}** wins!"
                emoji = "🎉"
                game_data["player1_wins"] += 1
            else:
                result_text = f"**{game_data['player2'].first_name}** wins!"
                emoji = "🎉"
                game_data["player2_wins"] += 1
            
            # Create play again button (only player1 can use it)
            play_again_button = [[InlineKeyboardButton("🔄 Play Again", callback_data="rps_play_again")]]
            
            # Add score to final text
            score_text = f"\n\n📊 **Score:**\n{game_data['player1'].first_name}: {game_data['player1_wins']} | {game_data['player2'].first_name}: {game_data['player2_wins']} | Ties: {game_data['ties']}"
            
            final_text = (f"{emoji} **Game Result**\n\n"
                         f"{result_text}\n\n"
                         f"**{game_data['player1'].first_name}'s choice:** {player1_choice_text}\n"
                         f"**{game_data['player2'].first_name}'s choice:** {player2_choice_text}"
                         f"{score_text}")
            
            try:
                await callback_query.message.edit_text(final_text, reply_markup=InlineKeyboardMarkup(play_again_button))
            except FloodWait as e:
                await callback_query.answer(f"Please wait {e.value} seconds before trying again due to rate limits.", show_alert=True)
                return
            except Exception as e:
                await callback_query.answer(f"Error updating game: {str(e)}", show_alert=True)
                return
            
            # Store game result for play again
            active_games[message_id] = {
                "type": "result",
                "player1": game_data["player1"],
                "player2": game_data.get("player2"),
                "start_time": time.time(),
                "player1_wins": game_data["player1_wins"],
                "player2_wins": game_data["player2_wins"],
                "ties": game_data["ties"]
            }
            
        else:
            # Check if this is a completed game (result type)
            if game_data.get("type") == "result":
                await callback_query.answer("This game has already finished. Use the Play Again button to start a new game.", show_alert=True)
            else:
                await callback_query.answer("This is not your turn/game!", show_alert=True)
            return

async def rps_play_again_callback(client: Client, callback_query):
    """Handle play again button."""
    if callback_query.data != "rps_play_again":
        return
    
    await callback_query.answer()
    
    message_id = callback_query.message.id
    if message_id not in active_games:
        await callback_query.message.edit_text("❌ This game has expired. Use /rps to start a new game.")
        return
    
    game_data = active_games[message_id]
    user = callback_query.from_user
    
    # Only player1 can start a new game
    if user.id != game_data["player1"].id:
        await callback_query.answer("Only the original player can start a new game!", show_alert=True)
        return
    
    # Check cooldown
    current_time = time.time()
    if current_time - game_data["start_time"] < 3:  # 3 second cooldown for play again
        await callback_query.answer("Please wait a moment before starting a new game.", show_alert=True)
        return
    
    # Create new game
    buttons = [
        [
            InlineKeyboardButton("🪨 Rock", callback_data="rps_rock"),
            InlineKeyboardButton("🧻 Paper", callback_data="rps_paper"),
            InlineKeyboardButton("✂️ Scissors", callback_data="rps_scissors")
        ]
    ]
    
    if "player2" in game_data and game_data["player2"]:
        # Player vs Player rematch
        new_game_data = {
            "type": "pvp",
            "player1": game_data["player1"],
            "player2": game_data["player2"],
            "player1_choice": None,
            "player2_choice": None,
            "current_turn": "player1",
            "start_time": current_time,
            "player1_wins": game_data.get("player1_wins", 0),
            "player2_wins": game_data.get("player2_wins", 0),
            "ties": game_data.get("ties", 0)
        }
        
        score_text = f"\n\n📊 **Current Score:**\n{game_data['player1'].first_name}: {game_data.get('player1_wins', 0)} | {game_data['player2'].first_name}: {game_data.get('player2_wins', 0)} | Ties: {game_data.get('ties', 0)}"
        
        text = f"🎮 **Rock Paper Scissors**\n\n{game_data['player1'].first_name} vs {game_data['player2'].first_name}\n\nWaiting for **{game_data['player1'].first_name}** to choose...\n\nRock, paper, or scissors? Choose wisely!{score_text}"
    else:
        # Player vs Bot rematch
        new_game_data = {
            "type": "pve",
            "player1": game_data["player1"],
            "player2": None,
            "player1_choice": None,
            "bot_choice": None,
            "start_time": current_time,
            "player_wins": game_data.get("player_wins", 0),
            "bot_wins": game_data.get("bot_wins", 0),
            "ties": game_data.get("ties", 0)
        }
        
        score_text = f"\n\n📊 **Current Score:**\nYou: {game_data.get('player_wins', 0)} | Bot: {game_data.get('bot_wins', 0)} | Ties: {game_data.get('ties', 0)}"
        
        text = f"🎮 **Rock Paper Scissors**\n\nYou vs Bot\n\nRock, paper, or scissors? Choose wisely!{score_text}"
    
    try:
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except FloodWait as e:
        await callback_query.answer(f"Please wait {e.value} seconds before starting a new game due to rate limits.", show_alert=True)
        return
    except Exception as e:
        await callback_query.answer(f"Error starting new game: {str(e)}", show_alert=True)
        return
    
    active_games[message_id] = new_game_data

def register_rps_handlers(client: Client):
    """Register RPS callback handlers with the client."""
    from pyrogram.handlers import CallbackQueryHandler
    
    client.add_handler(CallbackQueryHandler(
        rps_callback_handler, 
        filters.regex(r"^rps_")
    ))
