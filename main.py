import os
import json
import re
import random
import urllib.parse
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key)


class ChatRequest(BaseModel):
    message: str
    history: list = []


@app.get("/")
@app.get("/index.html")
async def read_root():
    return FileResponse("index.html")

@app.get("/manifest.json")
async def get_manifest():
    return FileResponse("manifest.json")

@app.get("/sw.js")
async def get_sw():
    return FileResponse("sw.js", media_type="application/javascript")


def get_latest_recipes():
    try:
        with open("recipes.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def search_recipe_in_db(query: str):
    # Eğer soru bir takip sorusuysa (örn: "kaç tane...", "kaç derece...") yeni yemek arama!
    follow_up_keywords = ["kaç", "ne kadar", "nasıl", "süre", "derece", "dakika", "var mı", "eklenir mi"]
    is_follow_up = any(kw in query.lower() for kw in follow_up_keywords) and len(query.split()) < 6

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
                # Sadece kelime tarif ADINDA geçiyorsa yüksek puan ver
                if word in name_lower:
                    score += 5
                else:
                    score += 1

        extra_words = set(re.findall(r"\w+", name_lower)) - query_words
        score -= len(extra_words) * 2

        if score > best_score:
            best_score = score
            best_match = item

    # EĞER takip sorusu soruluyorsa veya arama puanı yetersizse (5'ten küçükse) eşleşmeyi REDDET
    if is_follow_up or best_score < 5:
        return None

    return best_match


def generate_image_prompt_with_ai(dish_name: str) -> str:
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert food photography prompt generator. Convert the user's dish name into a short, highly detailed English prompt for image generation. Return ONLY the English prompt, no extra text, no quotation marks."
                },
                {"role": "user", "content": f"Dish: {dish_name}"}
            ],
            max_tokens=60,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"delicious traditional Turkish food {dish_name}"


def ask_gourmet_ai(user_query: str, history: list = []):
    matched_recipe = search_recipe_in_db(user_query)

    system_instruction = """
Sen GourmetAI adında samimi, esprili ve usta bir dijital şef asistansın.

KURALLAR:
1. Öncelikli olarak sohbet geçmişinde konuşulan yemeğe sadık kal.
2. Kullanıcı "kaç tane?", "kaç derece?" gibi detay soruları soruyorsa, sohbet geçmişinde en son verdiğin tarifin bilgilerine bakarak cevap ver.
3. Eğer açıkça yeni bir 'VERİTABANI BİLGİSİ' verilmişse, o yeni tarife göre cevap ver.
4. Yanıtlarında bolca lezzetli emoji kullan (👨‍🍳, 🍳, 🍲, 🍕, 😋).
"""

    messages_payload = [{"role": "system", "content": system_instruction}]

    # Sohbet geçmişini ekle
    for msg in history[-6:]:
        messages_payload.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

    image_prompt_subject = user_query

    if matched_recipe:
        recipe_title = matched_recipe.get("tarif_adi", matched_recipe.get("name", user_query))
        image_prompt_subject = recipe_title
        context_text = f"VERİTABANINDAN BULUNAN TARİF BİLGİSİ:\n{json.dumps(matched_recipe, ensure_ascii=False)}\n\nKULLANICI SORUSU: {user_query}"
        messages_payload.append({"role": "user", "content": context_text})
    else:
        messages_payload.append({"role": "user", "content": user_query})

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_payload,
        )
        reply_text = completion.choices[0].message.content

        # Resim sadece YENİ bir tarif eşleştiğinde üretilsin
        dynamic_image_url = ""
        if matched_recipe:
            ai_english_prompt = generate_image_prompt_with_ai(image_prompt_subject)
            prompt_text = f"professional food photography of {ai_english_prompt}, mouth-watering, highly detailed, 8k"
            safe_subject = urllib.parse.quote(prompt_text)
            random_seed = random.randint(1, 99999)
            dynamic_image_url = f"https://image.pollinations.ai/prompt/{safe_subject}?width=800&height=500&nologo=true&seed={random_seed}"

        return {"reply": reply_text, "image_url": dynamic_image_url}

    except Exception as e:
        print("Groq Hatası:", e)
        return {"reply": f"⚠️ Şefin fırınında bir aksaklık oldu: {str(e)}", "image_url": ""}


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    result = ask_gourmet_ai(request.message, request.history)
    return {"reply": result["reply"], "image_url": result["image_url"]}