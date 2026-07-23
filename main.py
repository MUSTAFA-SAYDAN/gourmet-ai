import os
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

app = FastAPI()
load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Dosyalar (PWA)
@app.get("/")
@app.get("/index.html")
async def read_index():
    return FileResponse("index.html")

@app.get("/manifest.json")
async def manifest():
    return FileResponse("manifest.json")

@app.get("/sw.js")
async def sw():
    return FileResponse("sw.js")

# Groq Bağlantısı
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.0,
    groq_api_key=GROQ_API_KEY
)

# recipes.json Verisini Esnek ve Güvenli Yükle
RECIPES = []
try:
    with open("recipes.json", "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        if isinstance(raw_data, list):
            RECIPES = raw_data
        elif isinstance(raw_data, dict):
            RECIPES = next((v for v in raw_data.values() if isinstance(v, list)), [raw_data])
    print(f"✅ {len(RECIPES)} adet tarif başarıyla yüklendi.", flush=True)
except Exception as e:
    print(f"❌ recipes.json okuma hatası: {e}", flush=True)

def stringify_item(item):
    """Obje, sözlük veya metin olan veriyi güvenli bir şekilde metne dönüştürür."""
    if isinstance(item, dict):
        return " ".join(str(v) for v in item.values())
    return str(item)


def get_latest_recipes():
    """recipes.json dosyasını anlık okur.
    Böylece yeni tarif eklediğinde komut çalıştırmana veya sunucuyu restart etmene GEREK KALMAZ."""
    try:
        with open("recipes.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ recipes.json okuma hatası: {e}")
        return []

    
def find_best_recipe(query: str):
    recipes = get_latest_recipes()  # <-- Anlık olarak güncel JSON'ı çeker!
    if not recipes:
        return None

    clean_query = query.lower().replace("tarifi", "").replace("nedir", "").strip()
    query_words = set(re.findall(r'\w+', query.lower()))
    
    best_match = None
    best_score = -999

    for item in recipes:  # <-- RECIPES yerine recipes kullanıyoruz
        if not isinstance(item, dict):
            continue
            
        name = str(item.get("tarif_adi", item.get("name", ""))).strip()
        name_lower = name.lower()
        
        # 1. BİREBİR TAM EŞLEŞME
        if clean_query == name_lower:
            best_match = item
            break
            
        ingredients = item.get("malzemeler", item.get("ingredients", []))
        
        if isinstance(ingredients, list):
            ing_str = " ".join([stringify_item(i) for i in ingredients])
        else:
            ing_str = stringify_item(ingredients)
            
        text_to_search = f"{name} {ing_str}".lower()
        
        score = 0
        for word in query_words:
            if len(word) > 2 and word in text_to_search:
                if word in name_lower:
                    score += 5
                else:
                    score += 1

        recipe_title_words = set(re.findall(r'\w+', name_lower))
        extra_words = recipe_title_words - query_words
        score -= len(extra_words) * 3
        
        if score > best_score:
            best_score = score
            best_match = item
    
    if not best_match:
        return None
        
    name = best_match.get("tarif_adi", best_match.get("name", "Tarif"))
    ingredients = best_match.get("malzemeler", best_match.get("ingredients", []))
    steps = best_match.get("yapilis_adimlari", best_match.get("steps", []))
    
    if isinstance(ingredients, list):
        ing_text = "\n".join([f"- {stringify_item(i)}" for i in ingredients])
    else:
        ing_text = stringify_item(ingredients)
        
    if isinstance(steps, list):
        step_text = "\n".join([f"{idx+1}. {stringify_item(s)}" for idx, s in enumerate(steps)])
    else:
        step_text = stringify_item(steps)
    
    return f"TARİF ADI: {name}\n\nMALZEMELER:\n{ing_text}\n\nYAPILIŞI:\n{step_text}"

@app.post("/ask/")
async def ask_question(question: str):
    try:
        context = find_best_recipe(question)
        
        # 🔍 FAISS VEYA ARAMA MOTORUNUN NE GETİRDİĞİNİ TERMINALDE GÖRELİM:
        print("\n--------------------------------------------------")
        print(f"❓ ARANAN SORU: {question}")
        print(f"📄 BULUNAN BAĞLAM (CONTEXT):\n{context}")
        print("--------------------------------------------------\n", flush=True)

        if not context:
            return {"answer": "Üzgünüm, aradığınız tarif dökümanda bulunamadı."}
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "Sen sadece sana verilen BAĞLAM dökümanına göre cevap veren profesyonel bir mutfak robotusun.\n\n"
                "KATI KURALLAR VE YANIT FORMATI:\n"
                "1. Yanıtına HER ZAMAN önce '### 🛒 Malzemeler' başlığı açarak dökümandaki tüm malzemeleri madde madde listeleyerek başla.\n"
                "2. Ardından '### 👩‍🍳 Yapılışı' başlığı açarak dökümandaki tüm adımları eksiksiz ve sıra numarasıyla dök.\n"
                "3. Sadece ve sadece dökümanda yazan bilgilere, malzemelere ve lezzet sırlarına sadık kal.\n"
                "4. Dökümanda açıkça yer almayan hiçbir malzemeyi veya pişirme yöntemini kafandan ekleme.\n"
                "5. Eğer dökümanda hem klasik hem de farklı bir varyasyon (örneğin hem Patates Kızartması hem Yoğurtlu Patates Kızartması) varsa, kullanıcının TAM İSTEDİĞİ spesifik tarifi seç.\n"
                "6. Eğer sorulan soru dökümandaki tariflerde hiçbir şekilde geçmiyorsa, doğrudan 'Bu bilgi dökümanda yoktur.' de.\n"
                "7. Tüm cevaplarını sadece ve sadece akıcı, temiz bir Türkçe ile ver."
            )),
            ("human", "BAĞLAM DÖKÜMANI:\n{context}\n\nSORU:\n{question}\n\nCEVAP:")
        ])
        
        chain = prompt | llm | StrOutputParser()
        response = chain.invoke({"context": context, "question": question})
        return {"answer": response.strip()}
        
    except Exception as e:
        print(f"❌ TAM HATA DETAYI: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


# Dışarıdan gelecek tarifin veri kalıbı (Schema)
class RecipeModel(BaseModel):
    tarif_adi: str
    malzemeler: List[str]
    yapilis_adimlari: List[str]

@app.post("/add-recipe/")
async def add_recipe(recipe: RecipeModel):
    try:
        new_recipe = recipe.model_dump()
        
        # 1. RAM'deki listeye ekle
        RECIPES.append(new_recipe)
        
        # 2. recipes.json dosyasına yaz
        with open("recipes.json", "w", encoding="utf-8") as f:
            json.dump(RECIPES, f, ensure_ascii=False, indent=2)
            
        # 3. YENİ EKLENEN KISIM: FAISS Vektör İndeksini Anında Güncelle
        recipe_text = f"Tarif Adı: {recipe.tarif_adi}\nMalzemeler: {', '.join(recipe.malzemeler)}\nYapılış: {' '.join(recipe.yapilis_adimlari)}"
        
        vectorstore.add_texts(texts=[recipe_text], metadatas=[new_recipe])
        vectorstore.save_local("faiss_mutfak_endeksi")
            
        return {
            "status": "success", 
            "message": f"'{recipe.tarif_adi}' başarıyla eklendi ve vektör indeksine işlendi!",
            "toplam_tarif_sayisi": len(RECIPES)
        }
    except Exception as e:
        print(f"❌ Tarif ekleme hatası: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Tarif eklenirken hata oluştu: {e}")