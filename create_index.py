import json
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

print("1. recipes.json okunuyor...")
with open("recipes.json", "r", encoding="utf-8") as f:
    recipes = json.load(f)

docs = []
for item in recipes:
    name = item.get("tarif_adi", item.get("name", "Tarif"))
    ingredients = item.get("malzemeler", item.get("ingredients", []))
    steps = item.get("yapilis_adimlari", item.get("steps", []))
    
    ing_text = "\n".join([f"- {i}" for i in ingredients]) if isinstance(ingredients, list) else str(ingredients)
    step_text = "\n".join([f"{idx+1}. {s}" for idx, s in enumerate(steps)]) if isinstance(steps, list) else str(steps)
    
    content = f"TARİF ADI: {name}\n\nMALZEMELER:\n{ing_text}\n\nYAPILIŞI:\n{step_text}"
    docs.append(Document(page_content=content, metadata={"name": name}))

print("2. Vektör veritabanı oluşturuluyor (Bu işlem 30-60 sn sürebilir)...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(docs, embeddings)

# Indeksi klasöre kaydet
vectorstore.save_local("faiss_mutfak_endeksi")
print("✅ BAŞARILI! 'faiss_mutfak_endeksi' klasörü oluşturuldu.")