import json
from google import genai
import firebase_admin
from firebase_admin import credentials, firestore

# ----- CONFIG -----
BOT_NAME = "Simanto"
CLIENT_ID = "client_12345"  # Change: client Firestore document ID

# Optional fallback key (if Firestore key missing)
from config import GEMINI_API_KEY as FALLBACK_GEMINI_KEY

# Firebase setup
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ----- LOAD MEMORY FROM FIRESTORE -----
def load_memory():
    doc_ref = db.collection("clients").document(CLIENT_ID).collection("chat_history").document("history")
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {"history": []}

def save_memory(memory):
    doc_ref = db.collection("clients").document(CLIENT_ID).collection("chat_history").document("history")
    doc_ref.set(memory)

memory = load_memory()

# ----- FETCH GEMINI API KEY FROM FIRESTORE -----
def get_gemini_key():
    try:
        doc = db.collection("clients").document(CLIENT_ID).collection("gemini_key").document("key").get()
        return doc.to_dict()["api_key"]
    except:
        return FALLBACK_GEMINI_KEY

GEMINI_API_KEY = get_gemini_key()
client = genai.Client(api_key=GEMINI_API_KEY)

# ----- CHAT FUNCTION -----
def chat_with_gemini(user_text):
    conversation = ""
    for msg in memory["history"]:
        conversation += f"User: {msg['user']}\nSimanto: {msg['bot']}\n"
    conversation += f"User: {user_text}\nSimanto:"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=conversation
    )
    bot_reply = response.text.strip()

    memory["history"].append({"user": user_text, "bot": bot_reply})
    save_memory(memory)
    return bot_reply

# ----- OPTIONAL: Real-time Firestore listener for Admin Panel updates -----
def on_bot_update(snapshot, changes, read_time):
    print("⚡ Bot settings updated from Admin Panel!")
    global GEMINI_API_KEY, client
    GEMINI_API_KEY = get_gemini_key()
    client = genai.Client(api_key=GEMINI_API_KEY)

bot_ref = db.collection("clients").document(CLIENT_ID).collection("bot_settings")
bot_ref.on_snapshot(on_bot_update)

# ----- MAIN LOOP -----
print(f"🤖 {BOT_NAME} is now running... (type 'exit' to quit)\n")

while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit", "bye"]:
        print(f"{BOT_NAME}: Bye shona ❤️")
        break
    reply = chat_with_gemini(user_input)
    print(f"{BOT_NAME}: {reply}\n")
