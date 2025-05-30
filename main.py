# main.py
import threading
import app
import bot

# run bot in thread
botThread = threading.Thread(target=bot.runBot())
botThread.start()

# run the app in the main thread
app.runApp()
