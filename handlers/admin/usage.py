import aiosqlite
import os
import tempfile
from datetime import datetime
from pyrogram import Client, types
from config import ADMIN_IDS

# ---------------------------
# Usagedata command
# ---------------------------
async def usagedata_command(client: Client, message: types.Message):
    # Check if sender is admin
    if message.from_user.id in ADMIN_IDS:
        # Parse command arguments
        command_parts = message.text.split(maxsplit=1)
        specific_command = command_parts[1].strip() if len(command_parts) > 1 else None
        
        async with aiosqlite.connect("db/usage.db") as connection:
            async with connection.cursor() as cursor:
                # Get all tables (commands)
                data = await cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = await data.fetchall()
                
                if not tables:
                    await message.reply("📊 No usage data available yet.")
                    return
                
                # If specific command is requested
                if specific_command:
                    # Check if the command exists
                    table_names = [table[0] for table in tables]
                    if specific_command not in table_names:
                        available_commands = ", ".join(table_names)
                        await message.reply(f"❌ Command '{specific_command}' not found.\n\nAvailable commands: {available_commands}")
                        return
                    
                    # Generate detailed report for specific command
                    await generate_specific_command_report(client, message, cursor, specific_command)
                    return
                
                # Collect all command statistics
                command_stats = []
                total_usage = 0
                total_chats = set()
                
                for table in tables:
                    table_name = table[0]
                    try:
                        # Get total usage for this command
                        usage_data = await cursor.execute(f"SELECT SUM(usage), COUNT(*), type FROM {table_name} GROUP BY type;")
                        command_usage = await usage_data.fetchall()
                        
                        command_total = 0
                        chat_count = 0
                        type_breakdown = {}
                        
                        for usage_sum, count, chat_type in command_usage:
                            command_total += usage_sum or 0
                            chat_count += count or 0
                            type_breakdown[chat_type] = {'usage': usage_sum or 0, 'count': count or 0}
                        
                        # Get unique chat IDs for this command
                        chat_data = await cursor.execute(f"SELECT id FROM {table_name};")
                        chat_ids = await chat_data.fetchall()
                        for chat_id in chat_ids:
                            total_chats.add(chat_id[0])
                        
                        command_stats.append({
                            'name': table_name,
                            'total_usage': command_total,
                            'chat_count': chat_count,
                            'type_breakdown': type_breakdown
                        })
                        
                        total_usage += command_total
                    except Exception as e:
                        # Handle any table structure issues
                        command_stats.append({
                            'name': table_name,
                            'total_usage': 0,
                            'chat_count': 0,
                            'type_breakdown': {}
                        })
                
                # Sort commands by usage count (descending)
                command_stats.sort(key=lambda x: x['total_usage'], reverse=True)
                
                # Calculate most active chats across all commands
                chat_totals = {}  # chat_id -> {'name': name, 'total_usage': total, 'commands_used': set, 'type': type}
                
                for table in tables:
                    table_name = table[0]
                    try:
                        chat_data = await cursor.execute(f"SELECT id, name, usage, type FROM {table_name};")
                        chat_records = await chat_data.fetchall()
                        
                        for chat_id, chat_name, usage, chat_type in chat_records:
                            if chat_id not in chat_totals:
                                chat_totals[chat_id] = {
                                    'name': chat_name,
                                    'total_usage': 0,
                                    'commands_used': set(),
                                    'type': chat_type
                                }
                            chat_totals[chat_id]['total_usage'] += usage
                            chat_totals[chat_id]['commands_used'].add(table_name)
                    except Exception:
                        continue
                
                # Sort chats by total usage
                most_active_chats = sorted(
                    chat_totals.items(), 
                    key=lambda x: x[1]['total_usage'], 
                    reverse=True
                )[:15]  # Top 15 most active chats
                
                # Build the complete report
                data_message = "BOT USAGE ANALYTICS REPORT\n"
                data_message += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                data_message += "=" * 50 + "\n\n"
                
                # Overall statistics
                data_message += "SUMMARY STATISTICS\n"
                data_message += f"Total Commands: {len(command_stats)}\n"
                data_message += f"Total Usage: {total_usage:,}\n"
                data_message += f"Unique Chats: {len(total_chats)}\n"
                
                if command_stats:
                    most_used = command_stats[0]
                    data_message += f"Most Used: /{most_used['name']} ({most_used['total_usage']:,} times)\n"
                
                data_message += "\n" + "=" * 50 + "\n\n"
                
                # Most active chats section
                data_message += "MOST ACTIVE CHATS\n\n"
                
                for i, (chat_id, chat_info) in enumerate(most_active_chats, 1):
                    display_name = chat_info['name'][:30] + "..." if len(chat_info['name']) > 30 else chat_info['name']
                    
                    type_emoji = {
                        'private': '👤',
                        'group': '👥',
                        'supergroup': '🏢',
                        'channel': '📢'
                    }.get(chat_info['type'].lower(), '❓')
                    
                    percentage = (chat_info['total_usage'] / total_usage * 100) if total_usage > 0 else 0
                    
                    data_message += f"#{i:2d}. {type_emoji} {display_name}\n"
                    data_message += f"     Total Usage: {chat_info['total_usage']:,} ({percentage:.1f}%)\n"
                    data_message += f"     Commands Used: {len(chat_info['commands_used'])}\n"
                    data_message += f"     Type: {chat_info['type'].title()}\n\n"
                
                data_message += "=" * 50 + "\n\n"
                
                # Detailed command breakdown
                data_message += "COMMAND BREAKDOWN\n\n"
                
                for i, cmd in enumerate(command_stats, 1):
                    # Command header with ranking
                    data_message += f"#{i}. /{cmd['name']}\n"
                    data_message += f"Total Uses: {cmd['total_usage']:,}\n"
                    data_message += f"Active Chats: {cmd['chat_count']}\n"
                    
                    # Chat type breakdown
                    if cmd['type_breakdown']:
                        data_message += "Usage by Type:\n"
                        for chat_type, stats in cmd['type_breakdown'].items():
                            percentage = (stats['usage'] / cmd['total_usage'] * 100) if cmd['total_usage'] > 0 else 0
                            data_message += f"  {chat_type.title()}: {stats['usage']:,} uses ({percentage:.1f}%) in {stats['count']} chats\n"
                    
                    data_message += "\n" + "-" * 30 + "\n\n"
                
                # Detailed chat information for top 3 commands
                data_message += "TOP COMMAND DETAILS\n\n"
                
                for cmd in command_stats[:3]:  # Top 3 commands only
                    data_message += f"/{cmd['name']} - Detailed View\n"
                    
                    try:
                        # Get individual chat data for this command
                        chat_data = await cursor.execute(
                            f"SELECT id, name, usage, type FROM {cmd['name']} ORDER BY usage DESC LIMIT 10;"
                        )
                        top_chats = await chat_data.fetchall()
                        
                        if top_chats:
                            data_message += "Top 10 Users/Chats:\n"
                            for j, (chat_id, chat_name, usage, chat_type) in enumerate(top_chats, 1):
                                # Truncate long names
                                display_name = chat_name[:25] + "..." if len(chat_name) > 25 else chat_name
                                data_message += f"  {j:2d}. [{chat_type.title()}] {display_name} - {usage:,} uses\n"
                        
                        data_message += "\n"
                    except Exception as e:
                        data_message += f"  Error loading details: {str(e)}\n\n"
                
                data_message += "=" * 50 + "\n"
                data_message += "End of Analytics Report"
        
        # Create temporary file and send it
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(data_message)
                temp_file_path = temp_file.name
            
            # Send the file
            filename = f"bot_usage_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            await message.reply_document(
                document=temp_file_path,
                file_name=filename,
                caption="📊 Bot Usage Analytics Report"
            )
            
            # Clean up the temporary file
            os.unlink(temp_file_path)
            
        except Exception as e:
            await message.reply(f"❌ Error generating report file: {str(e)}")
            
    else:
        await message.reply("❌ You're not authorized to use this command.")

async def generate_specific_command_report(client: Client, message: types.Message, cursor, command_name: str):
    """Generate detailed analytics report for a specific command."""
    try:
        # Get comprehensive data for the specific command
        data = await cursor.execute(f"SELECT id, name, usage, type, members, invite FROM {command_name} ORDER BY usage DESC;")
        all_records = await data.fetchall()
        
        if not all_records:
            await message.reply(f"📊 No usage data found for command '/{command_name}'.")
            return
        
        # Calculate statistics
        total_usage = sum(record[2] for record in all_records)
        unique_chats = len(all_records)
        
        # Group by chat type
        type_stats = {}
        for record in all_records:
            chat_type = record[3]
            if chat_type not in type_stats:
                type_stats[chat_type] = {'usage': 0, 'count': 0}
            type_stats[chat_type]['usage'] += record[2]
            type_stats[chat_type]['count'] += 1
        
        # Build detailed report
        report = f"DETAILED ANALYTICS REPORT - /{command_name}\n"
        report += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += "=" * 60 + "\n\n"
        
        # Summary statistics
        report += "COMMAND SUMMARY\n"
        report += f"Command: /{command_name}\n"
        report += f"Total Usage: {total_usage:,} times\n"
        report += f"Unique Chats: {unique_chats}\n"
        report += f"Average Usage per Chat: {total_usage / unique_chats:.2f}\n"
        
        if all_records:
            most_active = all_records[0]
            report += f"Most Active Chat: {most_active[1]} ({most_active[2]:,} uses)\n"
        
        report += "\n" + "=" * 60 + "\n\n"
        
        # Chat type breakdown
        report += "USAGE BY CHAT TYPE\n\n"
        for chat_type, stats in sorted(type_stats.items(), key=lambda x: x[1]['usage'], reverse=True):
            percentage = (stats['usage'] / total_usage * 100) if total_usage > 0 else 0
            avg_per_chat = stats['usage'] / stats['count'] if stats['count'] > 0 else 0
            
            type_emoji = {
                'private': '👤',
                'group': '👥',
                'supergroup': '🏢',
                'channel': '📢'
            }.get(chat_type.lower(), '❓')
            
            report += f"{type_emoji} {chat_type.title()}:\n"
            report += f"  Total Usage: {stats['usage']:,} ({percentage:.1f}%)\n"
            report += f"  Number of Chats: {stats['count']}\n"
            report += f"  Average per Chat: {avg_per_chat:.2f}\n\n"
        
        report += "=" * 60 + "\n\n"
        
        # Detailed chat list
        report += "DETAILED CHAT BREAKDOWN\n\n"
        report += f"{'Rank':<4} {'Chat Type':<12} {'Usage':<8} {'Chat Name'}\n"
        report += "-" * 60 + "\n"
        
        for i, (chat_id, chat_name, usage, chat_type, members, invite) in enumerate(all_records, 1):
            # Truncate long names for table format
            display_name = chat_name[:35] + "..." if len(chat_name) > 35 else chat_name
            
            type_emoji = {
                'private': '👤',
                'group': '👥',
                'supergroup': '🏢',
                'channel': '📢'
            }.get(chat_type.lower(), '❓')
            
            report += f"{i:<4} {type_emoji} {chat_type:<10} {usage:<8} {display_name}\n"
        
        report += "\n" + "=" * 60 + "\n\n"
        
        # Usage distribution analysis
        report += "USAGE DISTRIBUTION ANALYSIS\n\n"
        
        usage_values = [record[2] for record in all_records]
        usage_values.sort(reverse=True)
        
        # Percentiles
        def get_percentile(values, percentile):
            index = int(len(values) * percentile / 100)
            return values[min(index, len(values) - 1)]
        
        report += f"Highest Usage: {usage_values[0]:,}\n"
        report += f"90th Percentile: {get_percentile(usage_values, 90):,}\n"
        report += f"75th Percentile: {get_percentile(usage_values, 75):,}\n"
        report += f"50th Percentile (Median): {get_percentile(usage_values, 50):,}\n"
        report += f"25th Percentile: {get_percentile(usage_values, 25):,}\n"
        report += f"10th Percentile: {get_percentile(usage_values, 10):,}\n"
        report += f"Lowest Usage: {usage_values[-1]:,}\n\n"
        
        # Heavy users analysis
        heavy_user_threshold = get_percentile(usage_values, 90)
        heavy_users = [record for record in all_records if record[2] >= heavy_user_threshold]
        
        report += f"HEAVY USERS (90th percentile and above - {heavy_user_threshold:,}+ uses):\n"
        report += f"Number of Heavy Users: {len(heavy_users)}\n"
        report += f"Heavy User Usage: {sum(record[2] for record in heavy_users):,} ({sum(record[2] for record in heavy_users) / total_usage * 100:.1f}% of total)\n\n"
        
        for record in heavy_users[:10]:  # Top 10 heavy users
            display_name = record[1][:40] + "..." if len(record[1]) > 40 else record[1]
            report += f"  {record[3].title()}: {display_name} - {record[2]:,} uses\n"
        
        if len(heavy_users) > 10:
            report += f"  ... and {len(heavy_users) - 10} more heavy users\n"
        
        report += "\n" + "=" * 60 + "\n"
        report += f"End of Detailed Report for /{command_name}"
        
        # Create and send file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(report)
            temp_file_path = temp_file.name
        
        filename = f"{command_name}_detailed_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        await message.reply_document(
            document=temp_file_path,
            file_name=filename,
            caption=f"📊 Detailed Analytics Report for /{command_name}\n\n"
                   f"📈 Total Usage: {total_usage:,}\n"
                   f"💬 Unique Chats: {unique_chats}\n"
                   f"📊 Average per Chat: {total_usage / unique_chats:.2f}"
        )
        
        # Clean up
        os.unlink(temp_file_path)
        
    except Exception as e:
        await message.reply(f"❌ Error generating detailed report for '{command_name}': {str(e)}")