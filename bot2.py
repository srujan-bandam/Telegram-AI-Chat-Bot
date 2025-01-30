import os
import io
from PIL import Image
import logging
from serpapi import GoogleSearch
from pymongo.server_api import ServerApi
from google.cloud import vision
import google.generativeai as genai
from pymongo import MongoClient
import urllib.parse
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv

# Load environment variables
load_dotenv()



BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

client = MongoClient(MONGO_URI)
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
db = client['telegram_bot']
users_collection = db['users']
chats_collection = db['chat_history']
files_collection = db['file_metadata']

# Logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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
        await update.message.reply_text("Welcome! Please share your phone number.", reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Share Contact", request_contact=True)]], one_time_keyboard=True
        ))
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

'''async def image_handler(update: Update, context: CallbackContext):
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
        model = genai.GenerativeModel("gemini-pro-vision")

        # Send image to Gemini API for analysis
        response = model.generate_content([{"type": "image", "data": image_bytes}])
        answer = response.text if response and hasattr(response, 'text') else "No response from AI."

        # Store metadata in MongoDB
        files_collection.insert_one({"file_path": file_path, "bot_reply": answer})
        
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await update.message.reply_text("An error occurred while processing the image.") '''

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

        # Correct format for Gemini API
        response = model.generate_content([
            
            {"text": "Analyze this image and describe what you see."},
            { 
                "inline_data": {  
                    "mime_type": "image/jpeg",
                    "data": image_bytes
                }
            }
        ])

        answer = response.text if response and hasattr(response, 'text') else "No response from AI."

        # Store metadata in MongoDB
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

    serpapi_key = os.getenv("SERPAPI_KEY")  # Load API key from environment variables
    if not serpapi_key:
        await update.message.reply_text("Web search is unavailable. API key is missing.")
        return

    try:
        search = GoogleSearch({
            "q": query,
            "api_key": serpapi_key,
            "num": 5  # Get top 5 results
        })
        results = search.get_dict()

        # Extract search results
        if "organic_results" in results:
            search_results = results["organic_results"]
            response_text = "\n".join([f"🔗 [{res['title']}]({res['link']})" for res in search_results])
        else:
            response_text = "No relevant search results found."

        await update.message.reply_text(f"🔍 **Search results for:** `{query}`\n\n{response_text}", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text("An error occurred while searching the web.")

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.add_handler(MessageHandler(filters.PHOTO, image_handler))
    app.add_handler(CommandHandler("websearch", web_search))
    
    logger.info("Bot started...")
    app.run_polling()
