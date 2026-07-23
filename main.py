import os
import json
import re
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from groq import Groq

app = FastAPI()

load_dotenv()

# 🔑 API Anahtarını koda gömmek yerine .env dosyasından çekiyoruz:
groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key)

@app.get("/")
async def read_root():
    """Ana sayfayı (index.html) yükler"""
    return FileResponse("index.html")


def get_latest_recipes():
    try:
        with open("recipes.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def search_recipe_in_db(query: str):
    recipes = get_latest_recipes()
    clean_query = query.lower().replace("tarifi", "").replace("nedir", "").strip()
    query_words = set(re.findall(r'\w+', clean_query))
    
    best_match = None
    best_score = -999

    for item in recipes:
        if not isinstance(item, dict):
            continue
            
        name = str(item.get("tarif_adi", item.get("name", ""))).strip()
        name_lower = name.lower()
        
        if clean_query == name_lower:
            return item
            
        score = 0
        ingredients = item.get("malzemeler", item.get("ingredients", []))
        ing_str = " ".join([str(i) for i in ingredients]) if isinstance(ingredients, list) else str(ingredients)
        text_to_search = f"{name} {ing_str}".lower()
        
        for word in query_words:
            if len(word) > 2 and word in text_to_search:
                score += 5 if word in name_lower else 1

        extra_words = set(re.findall(r'\w+', name_lower)) - query_words
        score -= len(extra_words) * 3
        
        if score > best_score and score > 0:
            best_score = score
            best_match = item
            
    return best_match


def ask_gourmet_ai(user_query: str):
    matched_recipe = search_recipe_in_db(user_query)
    
    system_instruction = """
    Sen GourmetAI adında samimi, espirili, neşeli ve usta bir dijital şef asistanısın.
    
    KURALLAR:
    1. Sana 'VERİTABANI BİLGİSİ' verilmişse, O TARİFE %100 SADIK KALARAK malzemeleri ve yapılış adımlarını anlat.
    2. Veritabanı bilgisi YOKSA ve kullanıcı tarif soruyorsa, kendi şef bilginle yanıtla ama veritabanında olmadığını belirt.
    3. Kullanıcı sohbet ediyorsa ('nasılsın', 'merhaba' vb.) doğal, samimi ve neşeli bir şef gibi konuş.
    4. Yanıtlarında bolca lezzetli emoji kullan (👨‍🍳, 🍳, 🍲, 🍕).
    """

    context = ""
    if matched_recipe:
        context = f"VERİTABANINDAN BULUNAN TARİF BİLGİSİ:\n{json.dumps(matched_recipe, ensure_ascii=False)}\n\n"

    final_prompt = f"{context}KULLANICI MESAJI: {user_query}"

    try:
        # 🚀 Groq ile ışık hızında yanıt alıyoruz:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": final_prompt}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"🚨 Groq Hatası: {e}")
        return f"⚠️ Şefin fırınında bir aksaklık oldu: {str(e)}"


# 🚀 Ön Yüzün (Frontend) Çağırdığı Kapılar (/ask ve /chat)

# 1. Önce ChatRequest modelini tanımlıyoruz
class ChatRequest(BaseModel):
    message: str

# 2. Sonra Ön Yüzün Çağırdığı Kapıları (/ask ve /chat) açıyoruz
@app.get("/ask")
@app.post("/ask")
async def ask_endpoint(question: str = ""):
    reply = ask_gourmet_ai(question)
    return {"reply": reply, "response": reply, "answer": reply}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    reply = ask_gourmet_ai(request.message)
    return {"reply": reply, "response": reply, "answer": reply}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    reply = ask_gourmet_ai(request.message)
    return {"reply": reply, "response": reply, "answer": reply}