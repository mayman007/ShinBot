import asyncio
import datetime
import aiosqlite

async def init_timer_db():
    """Initialize the timers database table if it doesn't exist."""
    async with aiosqlite.connect("db/database.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS timers (
                    chat_id INTEGER,
                    user_id INTEGER,
                    end_time TEXT,
                    reason TEXT,
                    state TEXT,
                    message_id INTEGER
                )
            """)
            await connection.commit()

async def check_pending_timers(client):
    """
    Call this function once (in a background task) to schedule notifications
    for all timers that haven't expired.
    """
    # Ensure database and tables exist
    await init_timer_db()
    
    async with aiosqlite.connect("db/database.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT chat_id, user_id, end_time, reason, state, message_id FROM timers WHERE state='active'")
            rows = await cursor.fetchall()
            for row in rows:
                chat_id, user_id, end_time_str, reason, state, message_id = row
                end_time = datetime.datetime.fromisoformat(end_time_str)
                now = datetime.datetime.now()
                if end_time <= now:
                    end_message = "Your timer has ended."
                    if reason:
                        end_message += f" Reason: {reason}"
                    await client.send_message(chat_id, end_message, reply_to=message_id)
                    await cursor.execute(
                        "UPDATE timers SET state='ended' WHERE chat_id=? AND end_time=? AND reason=?",
                        (chat_id, end_time_str, reason)
                    )
                else:
                    delay = (end_time - now).total_seconds()
                    asyncio.create_task(schedule_timer(client, chat_id, delay, reason, message_id))
            await connection.commit()

async def schedule_timer(client, chat_id, delay, reason, message_id=None):
    """
    Sleeps for the specified delay, then notifies the user that the timer has ended.
    After sending a message, update the timer state to 'ended'.
    """
    await asyncio.sleep(delay)
    end_message = "Your timer has ended."
    if reason:
        end_message += f" Reason: {reason}"
        
    # Send the notification as a reply to the original message if message_id is provided
    if message_id:
        await client.send_message(chat_id, end_message, reply_to=message_id)
    else:
        await client.send_message(chat_id, end_message)
    
    # Update the timer state in the database
    async with aiosqlite.connect("db/database.db") as connection:
        async with connection.cursor() as cursor:
            now_str = datetime.datetime.now().isoformat()
            await cursor.execute(
                "UPDATE timers SET state='ended' WHERE chat_id=? AND end_time<=? AND reason=?",
                (chat_id, now_str, reason)
            )
            await connection.commit()