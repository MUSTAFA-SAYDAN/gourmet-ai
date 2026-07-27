import os
import json
import re
import urllib.parse
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key)


class ChatRequest(BaseModel):
    message: str
    history: list = []


class AddTextRecipeRequest(BaseModel):
    recipe_text: str


def get_latest_recipes():
    try:
        with open("recipes.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def generate_image_url(prompt_text: str) -> str:
    # 1. Porsiyon ve sayıları temizle (Örn: "1,5 İskender" -> "İskender")
    clean_text = re.sub(r'\b\d+([.,]\d+)?\b|\bporsiyon\b|\bkişilik\b', '', prompt_text, flags=re.IGNORECASE).strip()
    if not clean_text:
        clean_text = prompt_text

    english_prompt = clean_text

    # 2. Groq ile İngilizceye çevir
    try:
        translation_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a food photography prompt generator. Convert the Turkish food name into a concise English dish description (3-5 words). Example: 'Karnıyarık' -> 'Turkish stuffed eggplant with minced meat'. Reply ONLY with the English description."
                },
                {"role": "user", "content": clean_text}
            ],
            max_tokens=30,
            temperature=0.1
        )
        english_prompt = translation_response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Görsel çeviri hatası (Orijinal kelime kullanılacak): {e}")

    # 3. Pollinations AI URL oluştur
    clean_prompt = f"delicious professional food photography of {english_prompt}, appetizing, studio lighting, 4k"
    encoded_prompt = urllib.parse.quote(clean_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&nologo=true"

def is_follow_up_query(query: str, history: list) -> bool:
    query_lower = query.lower().strip()

    # Kullanıcı açıkça yeni bir tarif istemediyse
    explicit_new_recipe = any(kw in query_lower for kw in ["tarifi ver", "tarifini ver", "tarifi nedir", "nasıl yapılır", "nasıl pişer", "tarif", "tarifi", "tarifini", "hazırlanışı", "yapılışı"])
    if explicit_new_recipe:
        return False

    # Sohbet geçmişi varsa veya takip sorusu kalıpları içeriyorsa kesinlikle takip sorusudur
    follow_up_indicators = [
        "peki", "yani", "ama", "o zaman", "bunda", "bunun", "bu", "o",
        "kaç", "ne kadar", "nasıl", "süre", "derece", "dakika", "var mı",
        "eklenir mi", "kullanılıyor", "kullanılır", "konur", "konulur",
        "mı", "mi", "mu", "mü", "neden", "hangisi", "adet"
    ]

    if history and len(history) > 0:
        return True

    if any(re.search(rf"\b{re.escape(ind)}\b", query_lower) for ind in follow_up_indicators):
        return True

    return False


def search_recipe_in_db(query: str):
    recipes = get_latest_recipes()
    if not recipes:
        return None

    query_lower = query.lower().strip()
    
    stop_words = {"tarifi", "tarif", "nasıl", "nedir", "yapılır", "bana", "ver", "bir", "ve", "ile", "için", "hazırlanır", "lütfen", "var", "mı", "mi", "mu", "mü", "kaç", "peki"}
    words = [w for w in re.findall(r'\w+', query_lower) if len(w) > 2]
    keywords = [w for w in words if w not in stop_words]

    if not keywords:
        return None

    query_words_set = set(keywords)
    best_match = None
    best_score = float('inf')  # Düşük puan (az ceza) en iyi eşleşmedir

    for item in recipes:
        if not isinstance(item, dict):
            continue

        name = str(item.get("tarif_adi", item.get("name", ""))).strip().lower()
        if not name:
            continue

        name_words = re.findall(r'\w+', name)
        name_words_set = set(name_words)

        # 1. Kullanıcının aradığı tüm anahtar kelimeler tarif adında var mı?
        if query_words_set.issubset(name_words_set):
            
            # Birebir tam isim eşleşmesi varsa büyük ödül (-100 Puan)
            clean_query_name = " ".join(keywords)
            if query_lower == name or clean_query_name == name:
                score = -100
            else:
                # Aranan kelimeler dışındaki HER FAZLADAN KELİME İÇİN +10 CEZA PUANI
                extra_words_count = len(name_words) - len(keywords)
                score = extra_words_count * 10

            # Tek kelimelik genel aramalarda (örneğin sadece "limon") yanlış eşleşmeyi engelle
            if len(keywords) == 1 and keywords[0] in ["limon", "şeker", "su", "tuz", "un", "yağ"]:
                if score > 0:
                    continue

            # En az ceza puanı alan (kullanıcının aradığına en yakın olan) tarifi hafızada tut
            if score < best_score:
                best_score = score
                best_match = item

    return best_match


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


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    user_query = request.message
    history = request.history

    is_follow = is_follow_up_query(user_query, history)
    matched_recipe = None if is_follow else search_recipe_in_db(user_query)

    system_instruction = """
Sen GourmetAI adında samimi ve usta bir dijital Türk Mutfak Şefisin.

ÇOK ÖNEMLİ ÜÇ YANIT KURALIN VAR:

1. EĞER KULLANICI YENİ BİR TARİF İSTİYORSA:
İSTİSNASIZ BİREBİR MARKDOWN TARİF KARTINI KULLAN.

2. EĞER KULLANICI MEVCUT SOHBETLE İLGİLİ BİR DETAY/TAKİP SORUSU SORUYORSA (Örn: "Kaç patlıcan kullanılıyor?", "Fırın kaç derece?", "Şeker ne kadar?"):
- SOHBET GEÇMİŞİNDEKİ (ÖNCİKİ MESAJLARDAKİ) TARİFE BAK.
- ASLA "sohbet geçmişinde tarif yok" DEME. GEÇMİŞTE VERDİĞİN TARİFTEKİ MİKTARI SÖYLE.
- ASLA YENİ TARİF ŞABLONU/KARTI KULLANMA.
- Sadece sorulan soruya KISA VE NET CEVAP VER (Örn: "Tarifte 4 adet patlıcan kullanılıyor.").

3. PORSİYON VE MALZEME GERÇEKÇİLİĞİ KURALI:
- Kullanıcı porsiyon veya miktar belirttiğinde (Örn: "1,5 İskender", "2 kişilik karnıyarık"), miktar oranlarını gerçekçi bir mutfak mantığıyla ayarla. Sakın her malzemenin başına körü körüne aynı rakamı yazma (Örn: 1.5 porsiyon İskender için 150-200 gram et yeterlidir, asla 1.5 kg yazma!).
- Türk mutfağının geleneksel yemeklerine orijinalinde olmayan alakasız malzemeler (bezelye, mısır vb.) ekleme.
"""

    messages_payload = [{"role": "system", "content": system_instruction}]

    # SOHBET GEÇMİŞİNİ TEMİZLE VE GROQ'UN ANLAYACAĞI 'assistant' ROLÜNE ÇEVİR
    for msg in history[-10:]:  # Son 10 mesajı hafızada tut
        role = msg.get("role", "user")
        if role in ["bot", "chef", "system"]:
            role = "assistant"
        
        content = msg.get("content", "") or msg.get("text", "")
        if content:
            messages_payload.append({"role": role, "content": content})

    if matched_recipe:
        context_text = f"VERİTABANINDAN BULUNAN TARİF BİLGİSİ:\n{json.dumps(matched_recipe, ensure_ascii=False)}\n\nKULLANICI SORUSU: {user_query}\n\nLütfen bu veritabanı tarifini tam olarak sistem talimatında belirtilen Markdown şablonu formatında sun."
        messages_payload.append({"role": "user", "content": context_text})
    else:
        messages_payload.append({"role": "user", "content": user_query})

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_payload,
            temperature=0.2
        )
        reply_text = completion.choices[0].message.content

        # 📸 GÖRSEL TETİKLEME KONTROLÜ (ESNETİLDİ VE SAĞLAMLAŞTIRILDI)
        image_url = ""
        recipe_keywords = ["malzemeler", "hazırlanışı", "yapılışı", "tarif", "pişirme"]
        is_recipe_context = any(kw in reply_text.lower() for kw in recipe_keywords)

        # Takip sorusu değilse VE (veritabanından geldiyse VEYA gelen cevap bir tarif içeriyorsa)
        if not is_follow and (matched_recipe or is_recipe_context):
            food_subject = matched_recipe.get("tarif_adi") if (isinstance(matched_recipe, dict) and matched_recipe.get("tarif_adi")) else user_query
            image_url = generate_image_url(food_subject)

        return {"reply": reply_text, "image_url": image_url}

    except Exception as e:
        return {"reply": f"⚠️ Bir aksaklık oldu: {str(e)}", "image_url": ""}

@app.post("/add-recipe-text")
async def add_recipe_text(request: AddTextRecipeRequest):
    try:
        system_prompt = """
Convert the user's raw text recipe into a valid JSON object matching this exact structure:
{
  "tarif_adi": "Yemek Adı",
  "hazirlama_suresi": "Süre bilgisi",
  "kategori": "Kategori",
  "malzemeler": ["Malzeme 1", "Malzeme 2"],
  "hazirlanisi": "Aşama aşama yapılış anlatımı"
}
Return ONLY raw JSON object. No markdown, no explanation. Turkish language.
"""
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Dönüştürülecek Tarif:\n{request.recipe_text}"}
            ],
            temperature=0.1
        )

        raw_json_str = completion.choices[0].message.content.strip()
        raw_json_str = re.sub(r"^```json\s*", "", raw_json_str, flags=re.MULTILINE)
        raw_json_str = re.sub(r"^```\s*", "", raw_json_str, flags=re.MULTILINE).strip()

        new_recipe = json.loads(raw_json_str)
        new_name = new_recipe.get("tarif_adi", "").strip().lower()

        existing_recipes = get_latest_recipes()
        is_updated = False

        for idx, item in enumerate(existing_recipes):
            curr_name = str(item.get("tarif_adi", item.get("name", ""))).strip().lower()
            if curr_name == new_name or new_name in curr_name:
                existing_recipes[idx] = new_recipe
                is_updated = True
                break

        if not is_updated:
            existing_recipes.append(new_recipe)

        with open("recipes.json", "w", encoding="utf-8") as f:
            json.dump(existing_recipes, f, ensure_ascii=False, indent=2)

        recipe_name = new_recipe.get("tarif_adi", "Tarif")
        action = "güncellendi" if is_updated else "veritabanına eklendi"

        return {
            "status": "success",
            "message": f"'{recipe_name}' yapay zeka tarafından işlendi ve {action}!"
        }
    except Exception as e:
        return {"status": "error", "message": f"Dönüştürme hatası: {str(e)}"}