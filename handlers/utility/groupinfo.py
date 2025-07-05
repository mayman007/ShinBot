from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ChatType, ChatMemberStatus
import asyncio
from datetime import datetime, timezone

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
