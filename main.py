import os
import logging
import asyncio
from datetime import datetime
import aiohttp
from typing import Dict, List, Optional
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram.constants import ParseMode
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import pytz

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration - USE ENVIRONMENT VARIABLES
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 6973940391))
API_URL = "https://instagram-x-info.vercel.app/api/insta/r2x_4y"

# Channel info
CHANNEL_USERNAME = "@tech_master_a2z"
GROUP_USERNAME = "@tech_chatx"
CHANNEL_LINK = "https://t.me/tech_master_a2z"
GROUP_LINK = "https://t.me/tech_chatx"

# Database setup
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_member = Column(Boolean, default=False)
    join_date = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

# Database URL - Render এর জন্য
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///bot.db')

# PostgreSQL এর জন্য URL format ঠিক করুন
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
Base.metadata.create_all(engine)

# Thread-safe session তৈরি করুন
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
session_factory = scoped_session(SessionLocal)

def get_db():
    """Database session generator"""
    db = session_factory()
    try:
        yield db
    finally:
        db.close()

async def check_membership(user_id: int, bot):
    """Check if user joined channel and group"""
    try:
        # Check channel
        channel_status = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        # Check group
        group_status = await bot.get_chat_member(GROUP_USERNAME, user_id)
        
        return (channel_status.status in ['member', 'administrator', 'creator'] and 
                group_status.status in ['member', 'administrator', 'creator'])
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    
    db = session_factory()
    try:
        # Save user to database
        existing_user = db.query(User).filter(User.user_id == user.id).first()
        if not existing_user:
            new_user = User(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                last_active=datetime.utcnow()
            )
            db.add(new_user)
            db.commit()
        else:
            existing_user.last_active = datetime.utcnow()
            db.commit()
        
        # Check membership
        is_member = await check_membership(user.id, context.bot)
        
        if is_member:
            welcome_text = """👋 *Welcome to the tech zone!*

🚀 *আপডেট, টুলস ও গুরুত্বপূর্ণ তথ্য পেতে নিচের Channel ও Group গুলোতে অবশ্যই Join করুন*
⚡ *Developer by tech master* ⚡

✅ *You are already a member! Now you can use all features.*

📌 *Send any Instagram username to get info*"""
            
            keyboard = [
                [InlineKeyboardButton("👨‍💻 Developer Info", callback_data="dev_info")],
            ]
            
            if user.id == ADMIN_ID:
                keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            join_text = """👋 *Welcome to the tech zone!*

📢 *Please join our channel and group to use the bot:*

📢 *Official Channel:*
🔗 https://t.me/tech_master_a2z

💡 *Tech Chat box:*
🔗 https://t.me/tech_chatx

✅ *After joining, click the button below to verify.*"""
            
            keyboard = [
                [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
                [InlineKeyboardButton("💬 Join Group", url=GROUP_LINK)],
                [InlineKeyboardButton("✅ Verify Join", callback_data="verify")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                join_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    except Exception as e:
        logger.error(f"Error in start: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")
    finally:
        db.close()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Button callback handler"""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "verify":
            is_member = await check_membership(query.from_user.id, context.bot)
            
            if is_member:
                db = session_factory()
                user_record = db.query(User).filter(User.user_id == query.from_user.id).first()
                if user_record:
                    user_record.is_member = True
                    user_record.last_active = datetime.utcnow()
                    db.commit()
                db.close()
                
                await query.edit_message_text(
                    "✅ *Verified successfully! You can now use the bot.*\n\n"
                    "📌 *Send any Instagram username to get info.*",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    "❌ *You haven't joined both channel and group yet.*\n"
                    "Please join both and try again.",
                    parse_mode=ParseMode.MARKDOWN
                )
        
        elif query.data == "dev_info":
            dev_text = """*👨‍💻 Developer Information*

🤖 *Bot Developer:* tech master
👑 *Team Owner:* @gajarbotol
⚡ *Admin:* @victoriababe

🔧 *For support contact admin*"""
            
            await query.edit_message_text(
                dev_text,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif query.data == "admin_panel" and query.from_user.id == ADMIN_ID:
            db = session_factory()
            total_users = db.query(User).count()
            verified = db.query(User).filter(User.is_member == True).count()
            db.close()
            
            admin_text = f"""*⚙️ Admin Panel*

👥 *Total Users:* {total_users}
✅ *Verified:* {verified}
❌ *Pending:* {total_users - verified}

📌 *Admin Commands:*
/stats - Bot statistics
/broadcast - Broadcast message"""
            
            await query.edit_message_text(
                admin_text,
                parse_mode=ParseMode.MARKDOWN
            )
    
    except Exception as e:
        logger.error(f"Error in button_handler: {e}")
        await query.edit_message_text("❌ An error occurred. Please try again.")

async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Instagram username"""
    username = update.message.text.strip()
    user = update.effective_user
    
    # Check membership
    is_member = await check_membership(user.id, context.bot)
    if not is_member:
        await update.message.reply_text(
            "❌ *Please join our channel and group first.*\n\n"
            f"📢 Channel: {CHANNEL_LINK}\n"
            f"💬 Group: {GROUP_LINK}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Show loading
    msg = await update.message.reply_text(f"🔍 *Fetching @{username}...*", parse_mode=ParseMode.MARKDOWN)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/{username}", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    result = f"""*📱 Instagram Info*

👤 *Username:* @{data.get('username', username)}
📛 *Name:* {data.get('full_name', 'N/A')}"""
                    
                    followers = data.get('followers')
                    if followers is not None:
                        result += f"\n👥 *Followers:* {followers:,}"
                    
                    following = data.get('following')
                    if following is not None:
                        result += f"\n🤝 *Following:* {following:,}"
                    
                    posts = data.get('posts')
                    if posts is not None:
                        result += f"\n📸 *Posts:* {posts:,}"
                    
                    biography = data.get('biography')
                    if biography:
                        bio = biography[:300] + "..." if len(biography) > 300 else biography
                        result += f"\n📝 *Bio:*\n`{bio}`"
                    
                    await msg.delete()
                    await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
                else:
                    await msg.delete()
                    await update.message.reply_text(
                        f"❌ *Couldn't find @{username}*\nPlease check the username.",
                        parse_mode=ParseMode.MARKDOWN
                    )
    
    except asyncio.TimeoutError:
        await msg.delete()
        await update.message.reply_text(
            "❌ *Request timeout.*\nPlease try again later.",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Error fetching Instagram data: {e}")
        await msg.delete()
        await update.message.reply_text(
            "❌ *Error fetching data.*\nPlease try again later.",
            parse_mode=ParseMode.MARKDOWN
        )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin stats command"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied.")
        return
    
    db = session_factory()
    try:
        total = db.query(User).count()
        verified = db.query(User).filter(User.is_member == True).count()
        
        stats = f"""*📊 Bot Statistics*

👥 Total Users: {total}
✅ Verified: {verified}
❌ Pending: {total - verified}
🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
        
        await update.message.reply_text(stats, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await update.message.reply_text("❌ Error getting stats.")
    finally:
        db.close()

async def post_init(application: Application):
    """Post initialization"""
    await application.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("stats", "Bot statistics (admin only)")
    ])

def main():
    """Main function"""
    # Validate BOT_TOKEN
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        return
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram))
    
    # Get port from environment
    port = int(os.environ.get('PORT', 8080))
    
    # Check if we're in production (Render)
    if 'RENDER' in os.environ:
        # Get the Render external URL
        render_external_url = os.environ.get('RENDER_EXTERNAL_URL')
        
        if render_external_url:
            # Set webhook for Render
            logger.info(f"Setting webhook for URL: {render_external_url}")
            app.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=BOT_TOKEN,
                webhook_url=f"{render_external_url}/{BOT_TOKEN}",
                drop_pending_updates=True
            )
        else:
            logger.warning("RENDER_EXTERNAL_URL not found, using polling")
            app.run_polling(drop_pending_updates=True)
    else:
        # Local development - use polling
        logger.info("Starting bot with polling...")
        app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
