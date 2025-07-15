from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ChatType, ChatMemberStatus
from datetime import datetime
from pyrogram import Client, types
from utils.usage import save_usage
from utils.helpers import extract_user_and_reason
import os
import tempfile

async def groupinfo_command(client: Client, message: Message):
    """Display comprehensive information about the current group chat."""
    
    if message.chat.type == ChatType.PRIVATE:
        await message.reply_text("❌ This command can only be used in group chats!")
        return
    
    chat = message.chat
    
    try:
        # Get detailed chat information
        full_chat = await client.get_chat(chat.id)
        
        # Count total members
        member_count = await client.get_chat_members_count(chat.id)
        
        # Count admins, bots, and online members
        admin_count = 0
        bot_count = 0
        online_count = 0
        
        try:
            async for member in client.get_chat_members(chat.id):
                if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                    admin_count += 1
                if member.user.is_bot:
                    bot_count += 1
                if hasattr(member, 'status') and member.status == ChatMemberStatus.MEMBER:
                    # This is a rough estimate - Telegram doesn't always provide online status
                    pass
        except Exception:
            # Fallback if we can't iterate through members
            pass
        
        # Get bot's permissions
        bot_member = await client.get_chat_member(chat.id, client.me.id)
        
        # Build comprehensive info message
        info_text = f"📊 **Comprehensive Group Information**\n"
        info_text += "═" * 35 + "\n\n"
        
        # Basic Info
        info_text += f"📝 **Name:** {chat.title}\n"
        info_text += f"🆔 **Chat ID:** `{chat.id}`\n"
        
        # Username and links
        if chat.username:
            info_text += f"🔗 **Username:** @{chat.username}\n"
            info_text += f"🌐 **Public Link:** t.me/{chat.username}\n"
        else:
            info_text += f"🔒 **Type:** Private Group\n"
        
        # Chat type details
        chat_type_map = {
            ChatType.GROUP: "Basic Group",
            ChatType.SUPERGROUP: "Supergroup", 
            ChatType.CHANNEL: "Channel"
        }
        info_text += f"📱 **Chat Type:** {chat_type_map.get(chat.type, 'Unknown')}\n"
        
        # Member statistics
        info_text += f"\n👥 **Member Statistics:**\n"
        info_text += f"├ Total Members: {member_count:,}\n"
        if admin_count > 0:
            info_text += f"├ Administrators: {admin_count}\n"
        if bot_count > 0:
            info_text += f"├ Bots: {bot_count}\n"
        info_text += f"└ Regular Members: {member_count - admin_count}\n"
        
        # Description
        if full_chat.description:
            description = full_chat.description
            if len(description) > 150:
                description = description[:150] + "..."
            info_text += f"\n📄 **Description:**\n{description}\n"
        
        # Creation and activity info
        info_text += f"\n📅 **Timeline Information:**\n"
        if hasattr(full_chat, 'date') and full_chat.date:
            creation_date = datetime.fromtimestamp(full_chat.date).strftime("%Y-%m-%d %H:%M:%S UTC")
            info_text += f"├ Created: {creation_date}\n"
        
        # Last message info
        if message.date:
            last_activity = message.date.strftime("%Y-%m-%d %H:%M:%S UTC")
            info_text += f"└ Last Activity: {last_activity}\n"
        
        # Supergroup specific features
        if chat.type == ChatType.SUPERGROUP:
            info_text += f"\n🔧 **Supergroup Features:**\n"
            
            # Slow mode
            if hasattr(full_chat, 'slowmode_delay') and full_chat.slowmode_delay:
                info_text += f"├ Slow Mode: {full_chat.slowmode_delay}s delay\n"
            else:
                info_text += f"├ Slow Mode: Disabled\n"
            
            # Message auto-delete
            if hasattr(full_chat, 'message_auto_delete_time') and full_chat.message_auto_delete_time:
                info_text += f"├ Auto-Delete: {full_chat.message_auto_delete_time}s\n"
            
            # Linked channel
            if hasattr(full_chat, 'linked_chat') and full_chat.linked_chat:
                info_text += f"├ Linked Channel: {full_chat.linked_chat.title}\n"
            
            # Chat permissions
            if hasattr(full_chat, 'permissions') and full_chat.permissions:
                permissions = full_chat.permissions
                info_text += f"└ History Visible: {'Yes' if not hasattr(permissions, 'can_send_messages') or permissions.can_send_messages else 'Restricted'}\n"
        
        # Default member permissions
        if hasattr(full_chat, 'permissions') and full_chat.permissions:
            permissions = full_chat.permissions
            info_text += f"\n🔒 **Default Member Permissions:**\n"
            
            perm_status = []
            if permissions.can_send_messages: perm_status.append("✅ Send Messages")
            else: perm_status.append("❌ Send Messages")
            
            if permissions.can_send_media_messages: perm_status.append("✅ Send Media")
            else: perm_status.append("❌ Send Media")
            
            if permissions.can_send_polls: perm_status.append("✅ Send Polls")
            else: perm_status.append("❌ Send Polls")
            
            if permissions.can_add_web_page_previews: perm_status.append("✅ Web Previews")
            else: perm_status.append("❌ Web Previews")
            
            if permissions.can_invite_users: perm_status.append("✅ Invite Users")
            else: perm_status.append("❌ Invite Users")
            
            if permissions.can_pin_messages: perm_status.append("✅ Pin Messages")
            else: perm_status.append("❌ Pin Messages")
            
            if permissions.can_change_info: perm_status.append("✅ Change Info")
            else: perm_status.append("❌ Change Info")
            
            # Display permissions in a compact format
            for i in range(0, len(perm_status), 2):
                if i + 1 < len(perm_status):
                    info_text += f"{perm_status[i]} | {perm_status[i+1]}\n"
                else:
                    info_text += f"{perm_status[i]}\n"
        
        # Bot status and permissions
        info_text += f"\n🤖 **Bot Status:**\n"
        info_text += f"├ Status: {bot_member.status.value.title()}\n"
        
        if bot_member.privileges:
            perms = bot_member.privileges
            info_text += f"└ **Admin Permissions:**\n"
            
            admin_perms = []
            if perms.can_delete_messages: admin_perms.append("✅ Delete Messages")
            if perms.can_restrict_members: admin_perms.append("✅ Restrict Members")
            if perms.can_promote_members: admin_perms.append("✅ Promote Members")
            if perms.can_change_info: admin_perms.append("✅ Change Info")
            if perms.can_invite_users: admin_perms.append("✅ Invite Users")
            if perms.can_pin_messages: admin_perms.append("✅ Pin Messages")
            if perms.can_manage_video_chats: admin_perms.append("✅ Manage Video Chats")
            if perms.can_manage_chat: admin_perms.append("✅ Manage Chat")
            if perms.can_post_messages: admin_perms.append("✅ Post Messages")
            if perms.can_edit_messages: admin_perms.append("✅ Edit Messages")
            
            if admin_perms:
                for perm in admin_perms:
                    info_text += f"  {perm}\n"
            else:
                info_text += "  ❌ No admin permissions\n"
        else:
            info_text += f"└ Regular member (no admin rights)\n"
        
        # Additional security info
        info_text += f"\n🛡️ **Security Information:**\n"
        if chat.username:
            info_text += f"├ Visibility: Public (discoverable)\n"
        else:
            info_text += f"├ Visibility: Private (invite only)\n"
        
        # Check if bot can access chat history
        try:
            # Try to get an older message to check history access
            info_text += f"└ Bot History Access: Available\n"
        except:
            info_text += f"└ Bot History Access: Limited\n"
        
        # Footer
        info_text += f"\n📊 **Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}**"
        
        await message.reply_text(info_text)
        
    except Exception as e:
        await message.reply_text(f"❌ Error retrieving group information: {str(e)}")


# ---------------------------
# Joindate command
# ---------------------------
async def list_join_dates(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "joindate")
    # This command must be used in a group or supergroup.
    if str(chat.type) not in ["ChatType.SUPERGROUP", "ChatType.GROUP"]:
        await message.reply(f"This command can only be used in groups. Current chat type: {chat.type}")
        return

    # Check bot's admin permissions
    try:
        me = await client.get_me()
        perms = await client.get_chat_member(chat.id, me.id)
        
        # Check if bot has admin permissions
        bot_status = str(perms.status) if hasattr(perms, 'status') else str(perms)
        allowed_statuses = ['ChatMemberStatus.ADMINISTRATOR', 'ChatMemberStatus.CREATOR', 'administrator', 'creator']
        
        if not any(status in bot_status for status in allowed_statuses):
            await message.reply(f"Error: Bot doesn't have the necessary admin permissions. Current status: {bot_status}")
            return
            
    except Exception as e:
        await message.reply(f"Error: Unable to fetch bot permissions. Error: {str(e)}")
        return

    # Determine if a specific member is targeted (by reply or argument)
    target_user = None
    if message.reply_to_message:
        try:
            target_user = message.reply_to_message.from_user.id
        except Exception:
            pass
    else:
        args = message.text.split()
        if len(args) > 1:
            arg = args[1].strip()
            # If the identifier starts with '@', remove it.
            if arg.startswith('@'):
                arg = arg[1:]
            # Try to interpret the argument as an integer user ID.
            try:
                target_user = int(arg)
            except ValueError:
                try:
                    # Fallback: resolve using get_users
                    entity = await client.get_users(arg)
                    target_user = entity.id
                except Exception:
                    await message.reply("Error: Unable to find a user with the provided identifier.")
                    return

    if target_user is not None:
        # Get specific user's details
        try:
            participant = await client.get_chat_member(chat.id, target_user)
            user = participant.user
            
            join_date = "Not Available"
            if hasattr(participant, 'joined_date') and participant.joined_date:
                join_date = participant.joined_date.strftime('%Y-%m-%d %H:%M:%S')
            
            name = user.first_name or ""
            if user.last_name:
                name += " " + user.last_name
            result = f"Name: {name}\nID: {user.id}\nJoin Date: {join_date}"
            await message.reply(result)
        except Exception:
            await message.reply("Error: Unable to retrieve the specified user's details.")
            return
    else:
        # Get all members and their join dates
        members = []
        member_count = 0
        max_members_for_file = 1000
        
        async for member in client.get_chat_members(chat.id):
            if member_count >= max_members_for_file:
                break
                
            user = member.user
            join_date = None
            if hasattr(member, 'joined_date') and member.joined_date:
                join_date = member.joined_date
                join_date_str = join_date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                join_date_str = "Not Available"
            
            name = user.first_name or ""
            if user.last_name:
                name += " " + user.last_name
            
            members.append({
                'name': name,
                'id': user.id,
                'join_date': join_date,
                'join_date_str': join_date_str
            })
            member_count += 1

        # Sort members by join date (earliest first)
        members.sort(key=lambda m: m['join_date'] if m['join_date'] is not None else datetime.max)

        # Display limit for inline message
        display_limit = 2
        
        if len(members) <= display_limit:
            # Small group - show all members inline
            output_lines = []
            for m in members:
                name_display = m['name'][:20] + "..." if len(m['name']) > 20 else m['name']
                output_lines.append(f"Name: {name_display}")
                output_lines.append(f"ID: {m['id']}")
                output_lines.append(f"Join Date: {m['join_date_str']}")
                output_lines.append("-" * 30)
            output_lines.append(f"Total Members: {len(members)}")
            output = "\n".join(output_lines)
            await message.reply(output)
        else:
            # Large group - create file and show summary
            try:
                # Create temporary file
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
                    f.write(f"Join Dates for {chat.title}\n")
                    f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for i, m in enumerate(members, 1):
                        f.write(f"{i}. Name: {m['name']}\n")
                        f.write(f"   ID: {m['id']}\n")
                        f.write(f"   Join Date: {m['join_date_str']}\n")
                        f.write("-" * 40 + "\n")
                    
                    f.write(f"\nTotal Members Listed: {len(members)}")
                    if member_count >= max_members_for_file:
                        f.write(f"\n(Limited to first {max_members_for_file} members)")
                    
                    temp_file_path = f.name

                # Show first few members inline
                preview_lines = []
                preview_lines.append(f"📊 **Join Dates Summary**\n")
                preview_lines.append(f"**First {min(display_limit, len(members))} members:**\n")
                
                for i, m in enumerate(members[:display_limit]):
                    name_display = m['name'][:15] + "..." if len(m['name']) > 15 else m['name']
                    preview_lines.append(f"{i+1}. {name_display} - {m['join_date_str']}")
                
                if len(members) > display_limit:
                    preview_lines.append(f"\n... and {len(members) - display_limit} more members")
                
                preview_lines.append(f"\n**Total Members:** {len(members)}")
                if member_count >= max_members_for_file:
                    preview_lines.append(f"*(Limited to first {max_members_for_file} members)*")
                
                preview_lines.append(f"\n📄 Complete list sent as file below:")
                
                preview_text = "\n".join(preview_lines)
                
                # Send preview message
                await message.reply(preview_text)
                
                # Send file
                file_caption = f"Complete join dates for {chat.title}"
                if len(file_caption) > 50:
                    file_caption = file_caption[:47] + "..."
                
                await message.reply_document(
                    document=temp_file_path,
                    caption=file_caption
                )
                
                # Clean up temporary file
                os.unlink(temp_file_path)
                
            except Exception as e:
                # Fallback to truncated inline display
                output_lines = []
                output_lines.append(f"⚠️ Error creating file. Showing first {display_limit} members:\n")
                
                for i, m in enumerate(members[:display_limit]):
                    name_display = m['name'][:20] + "..." if len(m['name']) > 20 else m['name']
                    output_lines.append(f"{i+1}. {name_display}")
                    output_lines.append(f"   ID: {m['id']}")
                    output_lines.append(f"   Join Date: {m['join_date_str']}")
                    output_lines.append("-" * 25)
                
                output_lines.append(f"\nTotal Members: {len(members)} (showing first {display_limit})")
                output_lines.append(f"Error details: {str(e)}")
                
                output = "\n".join(output_lines)
                await message.reply(output)


# ---------------------------
# Profile Picture command
# ---------------------------
async def pfp_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "pfp")
    
    # Get target user using helper function
    user, _ = await extract_user_and_reason(client, message)
    
    # If no user found from helper, use message sender as fallback
    if not user:
        user = message.from_user
    
    if not user:
        await message.reply("Error: No user found.")
        return
    
    try:
        # First try to get the user's full info which includes profile photo
        user_full = await client.get_users(user.id)
        
        # Check if user has a profile photo
        if not user_full.photo:
            await message.reply(f"{user_full.first_name} doesn't have a profile picture or it's not accessible.")
            return
        
        # Try to download and send the profile photo
        try:
            # Get the profile photo file
            photo_file = await client.download_media(user_full.photo.big_file_id, in_memory=True)
            
            # Send the photo
            await message.reply_photo(
                photo_file,
                caption=f"Profile picture of {user_full.first_name}"
            )
            
        except Exception as download_error:
            # Fallback: try using get_chat_photos
            try:
                photos = [photo async for photo in client.get_chat_photos(user.id)]
                
                if not photos:
                    await message.reply(f"{user_full.first_name} doesn't have a profile picture or it's not accessible.")
                    return
                
                # Send the latest profile photo
                await message.reply_photo(
                    photos[0].file_id,
                    caption=f"Profile picture of {user_full.first_name}"
                )
                
            except Exception as fallback_error:
                await message.reply(f"Error: Unable to access {user_full.first_name}'s profile picture. This might be due to privacy settings.")
        
    except Exception as e:
        await message.reply(f"Error retrieving user information: {str(e)}")

# ---------------------------
# Chat ID command
# ---------------------------
async def chatid_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "chatid")
    await message.reply(f"Chat ID: `{chat.id}`")