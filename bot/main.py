import logging
import os
import sys
from datetime import datetime
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_engine, get_session, Event

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "👋 *Hello! I'm the Boston Tech Events Bot.*\n\n"
            "I can help you stay updated on the latest tech, startup, and networking events in Boston.\n\n"
            "Try these commands:\n"
            "📅 /events - Get the next 5 upcoming events\n"
            "🗓️ /today - Events happening today\n"
            "💡 /help - Show available commands"
        ),
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🤖 *Available Commands:*\n\n"
            "/start - Welcome message\n"
            "/events - List next 10 upcoming events\n"
            "/today - List events happening today\n"
            "/help - Show this help message"
        ),
        parse_mode=ParseMode.MARKDOWN
    )

async def events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    engine = get_engine()
    session = get_session(engine)
    
    try:
        events = session.query(Event).filter(
            Event.is_active == True,
            Event.date >= datetime.utcnow()
        ).order_by(Event.date).limit(10).all()
        
        if not events:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="No upcoming events found in the database. 😔"
            )
            return

        message = "📅 *Upcoming Boston Tech Events:*\n\n"
        for event in events:
            date_str = event.date.strftime('%a, %b %d @ %I:%M %p')
            message += f"🔹 *{event.title}*\n"
            message += f"   📅 {date_str}\n"
            if event.location:
                message += f"   📍 {event.location}\n"
            message += f"   🔗 [Link]({event.url})\n\n"
            
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    except Exception as e:
        logging.error(f"Error fetching events: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, something went wrong while fetching events."
        )
    finally:
        session.close()

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    engine = get_engine()
    session = get_session(engine)
    
    try:
        now = datetime.utcnow()
        # Simple approximation for "today" - this assumes UTC, might need adjustment for EST
        # Ideally we convert query to local time, but for now we'll just show next 24h
        
        events = session.query(Event).filter(
            Event.is_active == True,
            Event.date >= now,
            Event.date <= now.replace(hour=23, minute=59, second=59)
        ).order_by(Event.date).all()
        
        if not events:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="No events found for the rest of today. 🌙"
            )
            return

        message = "🗓️ *Events Happening Today:*\n\n"
        for event in events:
            date_str = event.date.strftime('%I:%M %p')
            message += f"🔹 *{event.title}*\n"
            message += f"   ⏰ {date_str}\n"
            message += f"   🔗 [Link]({event.url})\n\n"
            
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    finally:
        session.close()

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Your Chat ID is: `{update.effective_chat.id}`",
        parse_mode=ParseMode.MARKDOWN
    )

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        exit(1)
        
    application = ApplicationBuilder().token(token).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('events', events))
    application.add_handler(CommandHandler('today', today))
    application.add_handler(CommandHandler('id', id_command))
    
    print("Bot is polling...")
    application.run_polling()
