import json
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# 1. Dosyayı oku
with open("recipes.json", "r", encoding="utf-8") as f:
    recipes = json.load(f)

texts = []
metadatas = []

# 2. Her iki veri yapısını da destekleyen esnek döngü
for r in recipes:
    # Malzemeleri kontrol et (Sözlük mü yoksa Düz Metin mi?)
    malzeme_listesi = []
    for m in r.get("malzemeler", []):
        if isinstance(m, dict):
            # Eski format: {"isim": "domates", "miktar": 1, "birim": "adet"}
            isim = m.get("isim", "")
            miktar = m.get("miktar", "")
            birim = m.get("birim", "")
            malzeme_listesi.append(f"{miktar} {birim} {isim}".strip())
        elif isinstance(m, str):
            # Yeni format: "4 adet büyük boy patates"
            malzeme_listesi.append(m)

    # Yapılış adımlarını kontrol et
    yapilis = r.get("yapilis_adimlari", [])
    if isinstance(yapilis, list):
        yapilis_text = " ".join(yapilis)
    else:
        yapilis_text = str(yapilis)

    # Vektör veritabanına girecek zengin metin
    text = f"Tarif Adı: {r.get('tarif_adi', '')}\nMalzemeler: {', '.join(malzeme_listesi)}\nYapılış: {yapilis_text}"
    
    texts.append(text)
    metadatas.append(r)

# 3. Vektör indeksini baştan oluştur ve kaydet
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = FAISS.from_texts(texts=texts, embedding=embeddings, metadatas=metadatas)
vectorstore.save_local("faiss_mutfak_endeksi")

print("✅ İndeks her iki veri yapısına da uyumlu şekilde başarıyla güncellendi!")