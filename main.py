import os
import logging
import asyncio
from threading import Thread
from collections import Counter
from flask import Flask

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# =========================
# KEEP-ALIVE WEB SERVER (For Render)
# =========================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running 24/7 on Render!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# =========================
# BOT SETTINGS
# =========================
BOT_TOKEN = os.environ.get("BOT_TOKENID)
ADMIN_ID = 6029246309  # Telegram User ID

# States for Media Upload
GET_GROUP_NAME, UPLOADING_MEDIA = range(2)

# Memory Databases
DATABASE = {}            # Stores uploaded media collections
USERS = {}               # Stores bot user info
SEARCH_STATS = Counter() # Tracks top searches by users

# =========================
# KEYBOARDS
# =========================

admin_keyboard = [
    ["Video Upload", "Photos upload"],
    ["Admin Add History", "Bot Status"],
    ["Search Stats", "My Profile"]
]

admin_reply_markup = ReplyKeyboardMarkup(
    admin_keyboard,
    resize_keyboard=True
)

user_keyboard = [
    ["Support", "Movies & Shows"]
]

user_reply_markup = ReplyKeyboardMarkup(
    user_keyboard,
    resize_keyboard=True
)


def get_user_markup(user_id):
    if user_id == ADMIN_ID:
        return admin_reply_markup
    return user_reply_markup


def save_user(user):
    if not user:
        return
    USERS[user.id] = {
        "name": user.first_name or "Unknown",
        "username": f"@{user.username}" if user.username else "No Username"
    }


# =========================
# WELCOME MENU & BUTTONS
# =========================

async def send_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    inline_keyboard = [
        [
            InlineKeyboardButton("📢 Help", url="https://t.me/MS_Admin_08"),
            InlineKeyboardButton("⭐ Top Searching", callback_data="top_search")
        ],
        [
            InlineKeyboardButton("🌸 Join Update Channel ↗️", url="https://t.me/Realityshowsupload")
        ],
        [
            InlineKeyboardButton("♻️ Movies Search Channel ↗️", url="https://t.me/MS_TV_All_Shows_And_Movies")
        ],
        [
            InlineKeyboardButton("📞 Complaint Support 🛠️", url="https://t.me/MS_Admin_08")
        ],
        [
            InlineKeyboardButton("✉️ Owner Contact ✉️", url="https://t.me/MSsiam97")
        ]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard)

    welcome_text = (
        f"🎬 **Welcome to MS TV Bot!**\n\n"
        f"👋 Hello **{user.first_name}**!\n\n"
        f"📺 Your favorite Shows & Movies are here.\n"
        f"⚡ Search your favorite content easily.\n\n"
        f"Please select an option below:"
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(welcome_text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(welcome_text, reply_markup=markup, parse_mode="Markdown")


# =========================
# COMMAND HANDLERS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(update.effective_user)

    markup = get_user_markup(user_id)
    
    # Send temporary loading message
    loading_msg = await update.message.reply_text("Loading...", reply_markup=markup)
    
    # Send main welcome message
    await send_welcome(update, context)
    
    # Delete loading message immediately
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id, 
            message_id=loading_msg.message_id
        )
    except Exception as e:
        logging.error(f"Error deleting loading message: {e}")


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    await update.message.reply_text(
        "MS TV All Update 👇🏻\n\nhttps://t.me/MS_TV_All_Shows_And_Movies"
    )


# =========================
# AUTO DELETE JOB
# =========================

async def auto_delete_job(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    message_ids = job_data["message_ids"]

    for msg_id in message_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception as e:
            print(f"Error deleting message {msg_id}: {e}")


# =========================
# MEDIA UPLOAD CONVERSATION
# =========================

async def media_upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ Permission denied. Admin only area.",
            reply_markup=user_reply_markup
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "📝 Please enter the Keyword/Group Name for this collection:",
        reply_markup=ReplyKeyboardRemove()
    )
    return GET_GROUP_NAME


async def get_group_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_name = update.message.text.strip().lower()
    context.user_data["current_group"] = group_name

    if group_name not in DATABASE:
        DATABASE[group_name] = []

    done_keyboard = [["✅ Done"]]
    done_markup = ReplyKeyboardMarkup(done_keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"📁 Collection Name Set To: **{update.message.text}**\n\n"
        "Now send Videos, Photos, or Messages one by one.\n"
        "Click '✅ Done' when finished.",
        reply_markup=done_markup,
        parse_mode="Markdown"
    )
    return UPLOADING_MEDIA


async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_name = context.user_data.get("current_group")
    msg = update.message

    if not group_name:
        return

    if msg.video or msg.document:
        video_file = msg.video or msg.document
        DATABASE[group_name].append({
            "type": "video",
            "file_id": video_file.file_id,
            "caption": msg.caption or ""
        })
        await msg.reply_text("✅ Video added to collection!")

    elif msg.photo:
        photo_file_id = msg.photo[-1].file_id
        DATABASE[group_name].append({
            "type": "photo",
            "file_id": photo_file_id,
            "caption": msg.caption or ""
        })
        await msg.reply_text("✅ Photo added to collection!")

    elif msg.text and msg.text != "✅ Done":
        DATABASE[group_name].append({
            "type": "text",
            "text": msg.text
        })
        await msg.reply_text("✅ Text message added to collection!")


async def finish_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_name = context.user_data.get("current_group")
    total_items = len(DATABASE.get(group_name, []))

    await update.message.reply_text(
        f"🎉 Upload complete! Total {total_items} item(s) saved in collection '{group_name}'.",
        reply_markup=admin_reply_markup
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        "❌ Action cancelled.",
        reply_markup=get_user_markup(user_id)
    )
    return ConversationHandler.END


# =========================
# HELPER: SEND MEDIA (WITH AUTO DELETE)
# =========================

async def send_media_with_autodelete(chat_id, items, context: ContextTypes.DEFAULT_TYPE):
    sent_msg_ids = []

    warning_text = (
        "🚨 **IMPORTANT NOTICE / AUTO DELETE WARNING** 🚨\n\n"
        "📥 **Please Forward or Save Immediately!**\n"
        "Forward your requested items to your Saved Messages or any other chat right away.\n\n"
        "⏱️ **Time Limit:**\n"
        "Due to copyright protection and security reasons, this notice and all content "
        "will be **AUTOMATICALLY DELETED IN 30 MINUTES**!\n\n"
        "⚠️ You will not be able to access or view these messages after deletion. Save them now!"
    )

    warning_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=warning_text,
        parse_mode="Markdown"
    )
    sent_msg_ids.append(warning_msg.message_id)

    for item in items:
        item_type = item.get("type")
        if item_type == "video":
            m = await context.bot.send_video(
                chat_id=chat_id,
                video=item["file_id"],
                caption=item.get("caption", "")
            )
            sent_msg_ids.append(m.message_id)
        elif item_type == "photo":
            m = await context.bot.send_photo(
                chat_id=chat_id,
                photo=item["file_id"],
                caption=item.get("caption", "")
            )
            sent_msg_ids.append(m.message_id)
        elif item_type == "text":
            m = await context.bot.send_message(
                chat_id=chat_id,
                text=item["text"]
            )
            sent_msg_ids.append(m.message_id)

        await asyncio.sleep(0.3)

    context.job_queue.run_once(
        auto_delete_job,
        when=1800,  # 30 minutes
        data={
            "chat_id": chat_id,
            "message_ids": sent_msg_ids
        }
    )


# =========================
# PHOTOS / BROADCAST FUNCTION
# =========================

async def photos_upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    context.user_data["broadcast_mode"] = True
    await update.message.reply_text(
        "📸 **Broadcast Mode Activated**\n\n"
        "Send a Photo (with Caption) OR any Text Message.\n"
        "It will be automatically delivered to all bot users.\n\n"
        "Send /cancel to cancel."
    )


async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or not context.user_data.get("broadcast_mode"):
        return

    success_count = 0
    total_users = len(USERS)

    await update.message.reply_text(f"🚀 Broadcasting to {total_users} users...")

    for user_id in list(USERS.keys()):
        try:
            if update.message.photo:
                photo_file_id = update.message.photo[-1].file_id
                caption = update.message.caption or ""
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=photo_file_id,
                    caption=caption
                )
            elif update.message.text:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=update.message.text
                )
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            print(f"Failed sending broadcast to {user_id}: {e}")

    context.user_data["broadcast_mode"] = False
    await update.message.reply_text(
        f"✅ Broadcast completed!\n\n👥 Successfully sent to: {success_count}/{total_users} users",
        reply_markup=admin_reply_markup
    )


# =========================
# CALLBACK QUERY HANDLER
# =========================

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "top_search":
        if query.from_user.id != ADMIN_ID:
            await query.answer("❌ Search statistics are visible to Admin only!", show_alert=True)
            return

        if not SEARCH_STATS:
            await query.message.reply_text("📊 **Top Searches:**\n\nNo search history recorded yet.")
        else:
            msg = "📊 **Top Searched Keywords:**\n\n"
            for idx, (word, count) in enumerate(SEARCH_STATS.most_common(10), 1):
                msg += f"{idx}. `{word}` — {count} times\n"
            await query.message.reply_text(msg, parse_mode="Markdown")

    elif data.startswith("del_"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("❌ Admin action only!", show_alert=True)
            return

        group_name = data.replace("del_", "", 1)
        if group_name in DATABASE:
            del DATABASE[group_name]
            await query.edit_message_text(f"🗑️ Collection **'{group_name.title()}'** has been deleted successfully!", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ Collection not found or already deleted.")

    elif data.startswith("view_"):
        group_name = data.replace("view_", "", 1)
        if group_name in DATABASE:
            items = DATABASE[group_name]
            await query.message.reply_text(f"⚡ Sending {len(items)} item(s) for '{group_name}'...")
            await send_media_with_autodelete(query.message.chat_id, items, context)
        else:
            await query.message.reply_text("❌ Collection not found.")


# =========================
# MAIN MESSAGE HANDLER
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    lower_text = text.lower()
    chat_id = update.message.chat_id
    user = update.effective_user
    user_id = user.id

    save_user(user)

    if user_id == ADMIN_ID and context.user_data.get("broadcast_mode"):
        await broadcast_message(update, context)
        return

    if lower_text == "support":
        await update.message.reply_text("If You Any Problem Contact Admin @MS_Admin_08")

    elif lower_text == "movies & shows":
        await update.message.reply_text(
            "All Reality Show & Movie Update Here 👇🏻\n\n"
            "https://t.me/Realityshowsupload"
        )

    elif lower_text in ["photos upload", "search stats", "bot status", "admin add history"]:
        if user_id == ADMIN_ID:
            if lower_text == "photos upload":
                await photos_upload_start(update, context)
            elif lower_text == "search stats":
                if not SEARCH_STATS:
                    await update.message.reply_text("📊 **Search Statistics**\n\nNo search history recorded yet.")
                else:
                    msg = "📊 **Top User Search Queries:**\n\n"
                    for number, (word, count) in enumerate(SEARCH_STATS.most_common(20), 1):
                        msg += f"{number}. `{word}` — {count} times\n"
                    await update.message.reply_text(msg, parse_mode="Markdown")
            elif lower_text == "bot status":
                if not USERS:
                    await update.message.reply_text("📊 **Bot Status**\n\n👥 Total Joined Users: 0")
                else:
                    msg = f"📊 **Bot Status**\n\n👥 **Total Joined Users:** {len(USERS)}\n\n"
                    for number, (uid, u_info) in enumerate(USERS.items(), 1):
                        msg += (
                            f"{number}. 👤 **Name:** {u_info['name']}\n"
                            f"   🔗 **Username:** {u_info['username']}\n"
                            f"   🆔 **ID:** `{uid}`\n\n"
                        )
                    await update.message.reply_text(msg, parse_mode="Markdown")
            elif lower_text == "admin add history":
                if not DATABASE:
                    await update.message.reply_text("📜 Admin history is empty. No collection created yet.")
                else:
                    await update.message.reply_text("📁 **Your Uploaded Content Collections:**", parse_mode="Markdown")
                    for group_name, items in DATABASE.items():
                        inline_kb = InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("👁️ View Content", callback_data=f"view_{group_name}"),
                                InlineKeyboardButton("🗑 Delete Collection", callback_data=f"del_{group_name}")
                            ]
                        ])
                        await update.message.reply_text(
                            f"📁 **Collection Keyword:** `{group_name}`\n"
                            f"📦 **Total Items:** {len(items)}",
                            reply_markup=inline_kb,
                            parse_mode="Markdown"
                        )
        else:
            await update.message.reply_text(f"❌ Access Denied! Your ID (`{user_id}`) is not set as Admin ID.", parse_mode="Markdown")

    elif lower_text == "my profile":
        await update.message.reply_text(
            f"👤 **Your Profile:**\n"
            f"Name: {user.first_name}\n"
            f"ID: {user.id}"
        )

    elif lower_text in DATABASE:
        if user_id != ADMIN_ID:
            SEARCH_STATS[lower_text] += 1
        items = DATABASE[lower_text]
        await update.message.reply_text(f"⚡ Processing {len(items)} item(s)...")
        await send_media_with_autodelete(chat_id, items, context)

    else:
        if user_id != ADMIN_ID:
            SEARCH_STATS[lower_text] += 1
        await update.message.reply_text("Sorry, no content found with this name.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID and context.user_data.get("broadcast_mode"):
        await broadcast_message(update, context)


async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("update", "MS TV All Update")
    ])


# =========================
# MAIN EXECUTION
# =========================

if __name__ == "__main__":
    # Start Keep-Alive Server on separate thread
    Thread(target=run_web_server, daemon=True).start()

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex("^(Video Upload|Vedio Upload)$"),
                media_upload_start
            )
        ],
        states={
            GET_GROUP_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_group_name)
            ],
            UPLOADING_MEDIA: [
                MessageHandler(
                    filters.VIDEO | filters.Document.VIDEO | filters.PHOTO | (filters.TEXT & ~filters.Regex("^✅ Done$")),
                    receive_media
                ),
                MessageHandler(filters.Regex("^✅ Done$"), finish_upload)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("update", update_command))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot Start Now...")
    app.run_polling()
