import os
import json
import re
import random
import urllib.parse
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from groq import Groq

# 1. Uygulama ve Ortam Değişkenleri
app = FastAPI()
load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key)


# 2. Pydantic Veri Modeli
class ChatRequest(BaseModel):
    message: str


# 3. Ana Sayfa (Frontend) Servis Etme
@app.get("/")
async def read_root():
    """Ana sayfayı (index.html) yükler"""
    return FileResponse("index.html")


# 4. Veritabanı Yardımcı Fonksiyonları
def get_latest_recipes():
    try:
        with open("recipes.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def search_recipe_in_db(query: str):
    recipes = get_latest_recipes()
    clean_query = query.lower().replace("tarifi", "").replace("nedir", "").strip()
    query_words = set(re.findall(r"\w+", clean_query))

    best_match = None
    best_score = -999

    for item in recipes:
        if not isinstance(item, dict):
            continue

        name = str(item.get("tarif_adi", item.get("name", item.get("title", "")))).strip()
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

        extra_words = set(re.findall(r"\w+", name_lower)) - query_words
        score -= len(extra_words) * 3

        if score > best_score and score > 0:
            best_score = score
            best_match = item

    return best_match


# 5. Görsel İçin Yapay Zekaya İngilizce Prompt Ürettirme (Amelelik Yok!)
def generate_image_prompt_with_ai(dish_name: str) -> str:
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert food photography prompt generator. Convert the user's dish name into a short, highly detailed English prompt for image generation. Return ONLY the English prompt, no extra text, no quotation marks."
                },
                {
                    "role": "user",
                    "content": f"Dish: {dish_name}"
                }
            ],
            max_tokens=60,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("Image Prompt Gen Hatası:", e)
        return f"delicious traditional Turkish food {dish_name}"


# 6. Ana Şef Yanıtı Mantığı
def ask_gourmet_ai(user_query: str):
    matched_recipe = search_recipe_in_db(user_query)

    # Şef Personası ve Kuralları (Eksik olan değişken burasıydı)
    system_instruction = """
Sen GourmetAI adında samimi, esprili, neşeli ve usta bir dijital şef asistansın.

KURALLAR:
1. Sana 'VERİTABANI BİLGİSİ' verilmişse, O TARİFE %100 SADIK KALARAK malzemeleri ve yapılışını anlat.
2. Veritabanı bilgisi YOKSA ve kullanıcı tarif soruyorsa, kendi şef bilginle leziz bir tarif ver.
3. Kullanıcı sohbet ediyorsa ('nasılsın', 'merhaba' vb.) doğal, samimi ve neşeli yanıt ver.
4. Yanıtlarında bolca lezzetli emoji kullan (👨‍🍳, 🍳, 🍲, 🍕, 😋).
"""

    context = ""
    image_prompt_subject = user_query

    if matched_recipe:
        recipe_title = matched_recipe.get(
            "tarif_adi",
            matched_recipe.get("name", matched_recipe.get("title", user_query))
        )
        image_prompt_subject = recipe_title
        context = f"VERİTABANINDAN BULUNAN TARİF BİLGİSİ:\n{json.dumps(matched_recipe, ensure_ascii=False)}\n\n"

    final_prompt = f"{context}KULLANICI MESAJI: {user_query}"

    try:
        # A) Şefin Türkçe Yanıtını Üret
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": final_prompt},
            ],
        )
        reply_text = completion.choices[0].message.content

        # B) Görsel İçin İngilizce Tanımı Groq'a Ürettir
        ai_english_prompt = generate_image_prompt_with_ai(image_prompt_subject)
        
        # C) Dinamik ve Kaliteli Görsel Linki Oluştur
        prompt_text = f"professional food photography of {ai_english_prompt}, mouth-watering, highly detailed, 8k"
        safe_subject = urllib.parse.quote(prompt_text)
        random_seed = random.randint(1, 99999)
        
        dynamic_image_url = f"https://image.pollinations.ai/prompt/{safe_subject}?width=800&height=500&nologo=true&seed={random_seed}"

        return {"reply": reply_text, "image_url": dynamic_image_url}

    except Exception as e:
        print("Groq Hatası:", e)
        return {
            "reply": f"⚠️ Şefin fırınında bir aksaklık oldu: {str(e)}",
            "image_url": ""
        }


# 7. Rotalar (Endpoints)
@app.get("/ask")
@app.post("/ask")
async def ask_endpoint(question: str = ""):
    result = ask_gourmet_ai(question)
    return {"reply": result["reply"], "image_url": result["image_url"]}


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    result = ask_gourmet_ai(request.message)
    return {"reply": result["reply"], "image_url": result["image_url"]}