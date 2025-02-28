import aiosqlite
from telethon.tl.types import Chat, Channel, User

async def save_usage(chat_object, command_name: str):
    # Check for groups/supergroups:
    if isinstance(chat_object, Chat) or (isinstance(chat_object, Channel) and getattr(chat_object, 'megagroup', False)):
        chat_id = str(chat_object.id)
        chat_name = str(chat_object.title)
        # Telethon objects don't have a 'type' attribute, so we set it manually:
        chat_type = "group" if isinstance(chat_object, Chat) else "supergroup"
        chat_members = "idk"
        chat_invite = "idk"
    # Check for private chats:
    elif isinstance(chat_object, User):
        chat_id = str(chat_object.id)
        # Use username if available, else first_name
        chat_name = str(chat_object.username) if chat_object.username else str(chat_object.first_name)
        chat_type = "private"
        chat_members = "_"
        chat_invite = "_"
    else:
        # Fallback for any other type
        chat_id = str(chat_object.id)
        chat_name = "Unknown"
        chat_type = "Unknown"
        chat_members = "_"
        chat_invite = "_"

    async with aiosqlite.connect("db/usage.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {command_name} (id TEXT, name TEXT, usage INTEGER, type TEXT, members TEXT, invite TEXT)"
            )
            await cursor.execute(f"SELECT * FROM {command_name} WHERE id = ?", (chat_id,))
            row = await cursor.fetchone()
            if row is None:
                await cursor.execute(
                    f"INSERT INTO {command_name} (id, name, usage, type, members, invite) VALUES (?, ?, ?, ?, ?, ?)",
                    (chat_id, chat_name, 1, chat_type, chat_members, chat_invite),
                )
            else:
                await cursor.execute(
                    f"UPDATE {command_name} SET usage = ? WHERE id = ?",
                    (row[2] + 1, chat_id)
                )
            await connection.commit()
