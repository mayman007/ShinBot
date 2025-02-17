import aiosqlite

async def save_usage(chat_object, command_name: str):
    if chat_object.type in ['group', 'supergroup']:
        chat_id = str(chat_object.id)
        chat_name = str(chat_object.title)
        chat_type = str(chat_object.type)
        chat_members = "idk"
        chat_invite = "idk"
    elif chat_object.type in ['private', 'bot']:
        chat_id = str(chat_object.id)
        chat_name = str(chat_object.username if chat_object.username else chat_object.first_name)
        chat_type = str(chat_object.type)
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
                await cursor.execute(f"UPDATE {command_name} SET usage = ? WHERE id = ?", (row[2] + 1, chat_id))
            await connection.commit()
