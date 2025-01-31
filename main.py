import os
import io
import logging
from flask import Flask, request
from PIL import Image
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import certifi
from PyPDF2 import PdfReader
from telegram import Update, Bot, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import google.generativeai as genai
from serpapi import GoogleSearch





# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Example: "https://your-app.onrender.com"

genai.configure(api_key=GEMINI_API_KEY)

# MongoDB Connection
ca = certifi.where()
client = MongoClient(MONGO_URI, server_api=ServerApi('1'), tlsCAFile=ca)
db = client['telegram_bot']
users_collection = db['users']
chats_collection = db['chat_history']
files_collection = db['file_metadata']

# Initialize Flask
app = Flask(__name__)

# Logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram Bot
bot = Bot(token=BOT_TOKEN)


telegram_app = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    chat_id = update.message.chat_id
    existing_user = users_collection.find_one({"chat_id": chat_id})
    
    if not existing_user:
        users_collection.insert_one({
            "first_name": user.first_name,
            "username": user.username,
            "chat_id": chat_id,
            "phone_number": None
        })
        await update.message.reply_text(
            "Welcome! Please share your phone number.",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("Share Contact", request_contact=True)]],
                one_time_keyboard=True
            )
        )
    else:
        await update.message.reply_text("You're already registered!")

async def contact_handler(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    phone_number = update.message.contact.phone_number
    users_collection.update_one({"chat_id": chat_id}, {"$set": {"phone_number": phone_number}})
    await update.message.reply_text("Phone number saved! You can start chatting now.")

async def chat(update: Update, context: CallbackContext):
    user_input = update.message.text
    chat_id = update.message.chat_id
    
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(user_input)
        bot_reply = response.text if response and hasattr(response, 'text') else "Sorry, I couldn't process that."
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        bot_reply = "An error occurred while processing your request."
    
    chats_collection.insert_one({"chat_id": chat_id, "user_input": user_input, "bot_reply": bot_reply})
    await update.message.reply_text(bot_reply)

async def image_handler(update: Update, context: CallbackContext):
    try:
        photo = update.message.photo[-1]  # Get highest resolution photo
        file = await context.bot.get_file(photo.file_id)
        file_path = f"downloads/{photo.file_id}.jpg"
        await file.download_to_drive(file_path)
        
        image = Image.open(file_path)

        # Convert image to byte array
        with io.BytesIO() as output:
            image.save(output, format="JPEG")
            image_bytes = output.getvalue()

        # Load Gemini model
        model = genai.GenerativeModel("gemini-1.5-flash")

        response = model.generate_content([
            "Analyze this image and describe what you see.",
            {"mime_type": "image/jpeg", "data": image_bytes}
        ])

        answer = response.text if response and hasattr(response, 'text') else "No response from AI."

        files_collection.insert_one({"file_path": file_path, "bot_reply": answer})
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await update.message.reply_text("An error occurred while processing the image.")

async def web_search(update: Update, context: CallbackContext):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Please provide a search query.")
        return

    if not SERPAPI_KEY:
        await update.message.reply_text("Web search is unavailable. API key is missing.")
        return

    try:
        search = GoogleSearch({"q": query, "api_key": SERPAPI_KEY, "num": 5})
        results = search.get_dict()

        if "organic_results" in results:
            search_results = results["organic_results"]
            response_text = "\n".join([f"🔗 [{res['title']}]({res['link']})" for res in search_results])
        else:
            response_text = "No relevant search results found."

        await update.message.reply_text(f"🔍 **Search results for:** `{query}`\n\n{response_text}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in web search: {e}")
        await update.message.reply_text("An error occurred while searching the web.")

async def pdf_handler(update: Update, context: CallbackContext):
    document = update.message.document
    if document.mime_type != "application/pdf":
        await update.message.reply_text("Please send a PDF file.")
        return

    file = await context.bot.get_file(document.file_id)
    file_name = document.file_name
    file_path = f"downloads/{file_name}"
    await file.download_to_drive(file_path)

    content = extract_pdf_text(file_path)

    if content:
        description = await analyze_content(content)
        files_collection.insert_one({"file_path": file_path, "bot_reply": description})
        await update.message.reply_text(f"Analyzed content from PDF:\n\n{description}")
    else:
        await update.message.reply_text("Unable to extract text from the PDF.")

def extract_pdf_text(file_path: str):
    try:
        with open(file_path, "rb") as file:
            pdf_reader = PdfReader(file)
            text = "".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return None

async def analyze_content(content: str):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(content)
        return response.text if response and hasattr(response, 'text') else "Sorry, no analysis available."
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        return "Error during analysis."

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    app.bot.update_queue.put(update)  # Put update in the queue for processing
    return "OK", 200


# Set webhook on startup
if __name__ == "__main__":
    # Start Flask server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), threaded=True)

    # Build and configure the Telegram bot application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    application.add_handler(MessageHandler(filters.PHOTO, image_handler))
    application.add_handler(CommandHandler("websearch", web_search))
    application.add_handler(MessageHandler(filters.Document.ALL, pdf_handler))  # PDF file handler

    logger.info("Bot started...")

    # Run bot with webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        url_path=BOT_TOKEN,  # Telegram requires the bot token as the URL path
        webhook_url=f"https://telegram-ai-chat-bot-fvak.onrender.com/{BOT_TOKEN}"  # Replace with your Render URL
    )


