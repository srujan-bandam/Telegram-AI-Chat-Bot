# 📌 Telegram Bot with Gemini AI & File Analysis

🚀 **A powerful Telegram bot that integrates Google Gemini AI for chat, image, and file analysis.**

---

## ✨ Features

✅ **User Registration** - Stores user details (username, phone number, chat ID) in MongoDB.\
✅ **AI-Powered Chat** - Uses Google Gemini API to generate intelligent responses.\
✅ **Image Analysis** - Analyzes images (JPG, PNG) and provides descriptions.\
✅ **PDF & File Analysis** - Extracts text from PDFs and other files, analyzes content using Gemini, and stores metadata.\
✅ **Web Search** - Fetches summarized search results using SerpAPI.

---

## 🛠️ Tech Stack

- **Python** 🐍
- **python-telegram-bot** 🤖
- **Google Gemini API** 🤖🔍
- **MongoDB** 🗄️
- **PyPDF2** 📄
- **PIL (Pillow)** 🖼️
- **SerpAPI** 🔎

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository

```bash
 git clone https://github.com/yourusername/telegram-bot-gemini.git
 cd telegram-bot-gemini
```

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Create a `.env` File

```ini
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
MONGO_URI=your-mongodb-uri
GEMINI_API_KEY=your-gemini-api-key
SERPAPI_KEY=your-serpapi-key
```

### 4️⃣ Run the Bot

```bash
python bot.py
```

---

## 📸 Image & File Analysis

The bot can analyze:

- **Images** (JPG, PNG) and describe them using AI.
- **PDFs** and extract text for AI-powered summarization.

---

## 🎯 Usage

1️⃣ **Start the Bot** `/start`\
2️⃣ **Chat with AI** (Send messages directly)\
3️⃣ **Analyze Images** (Send an image)\
4️⃣ **Analyze PDFs & Files** (Send a PDF or document)\
5️⃣ **Web Search** `/websearch <query>`

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

---

## 🔗 Connect

📧 Email: [srujanbandam2003@example.com](mailto\:srujanbandam2003@example.com)\
🌍 GitHub: [srujan-bandam](https://github.com/srujan-bandam)

