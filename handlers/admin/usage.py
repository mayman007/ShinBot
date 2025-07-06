import asyncio
import aiosqlite
from pyrogram import Client, types
from config import ADMIN_IDS

# ---------------------------
# Usagedata command
# ---------------------------
async def usagedata_command(client: Client, message: types.Message):
    # Check if sender is admin
    if message.from_user.id in ADMIN_IDS:
        data_message = "Here is all the usage data!\n"
        async with aiosqlite.connect("db/usage.db") as connection:
            async with connection.cursor() as cursor:
                data = await cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = await data.fetchall()
                for table in tables:
                    table_name = table[0]
                    data_message += "===================\n\n"
                    data_message += f"**{table_name}**\n"
                    data = await cursor.execute(f"SELECT * FROM {table_name};")
                    rows = await data.fetchall()
                    for row in rows:
                        data_message += (
                            f"- Chat ID: {row[0]}\n"
                            f"- Chat Name: **{row[1]}**\n"
                            f"- Usage Count: **{row[2]}**\n"
                            f"- Chat Type: {row[3]}\n"
                        )
                        # Check if row has enough elements before accessing them
                        if len(row) > 4:
                            data_message += f"- Chat Members: {row[4]}\n"
                        if len(row) > 5:
                            data_message += f"- Chat Invite: {row[5]}\n"
                        data_message += "\n"
        limit = 3800
        if len(data_message) > limit:
            parts = [data_message[i: i + limit] for i in range(0, len(data_message), limit)]
            for part in parts:
                await message.reply(part)
                await asyncio.sleep(0.5)
        else:
            await message.reply(data_message)
    else:
        await message.reply("You're not allowed to use this command")