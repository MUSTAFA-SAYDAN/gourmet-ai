import json
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

def json_veri_setini_islemle(json_yolu: str):
    if not os.path.exists(json_yolu):
        print(f"❌ HATA: {json_yolu} dosyası bulunamadı! Lütfen dosyayı proje klasörüne kaydettiğinizden emin olun.")
        return

    print("⏳ JSON veri seti okunuyor...")
    with open(json_yolu, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    hazir_metinler = []
    
    print(f"🧠 Toplam {len(data)} adet yemek tarifi analiz ediliyor...")
    for recipe in data:
        tarif_adi = recipe.get("tarif_adi", "Bilinmeyen Yemek")
        kategori = recipe.get("kategori", "Genel")
        
        # Malzemeleri miktar ve birimleriyle düzgün bir liste haline getiriyoruz
        malzemeler_listesi = []
        for m in recipe.get("malzemeler", []):
            isim = m.get("isim", "")
            miktar = m.get("miktar", "")
            birim = m.get("birim", "")
            malzemeler_listesi.append(f"- {isim}: {miktar} {birim}".strip(": "))
        
        malzemeler_str = "\n".join(malzemeler_listesi)
        hazirlanis = recipe.get("hazirlanisi", recipe.get("tarif", "Dökümanda hazırlanış adımı belirtilmemiştir."))
        
        # Yapay zekaya verilecek temiz metin şablonu
        tek_metin = (
            f"YEMEK ADI: {tarif_adi}\n"
            f"KATEGORİ: {kategori}\n"
            f"MALZEMELER:\n{malzemeler_str}\n"
            f"HAZIRLANIŞI:\n{hazirlanis}\n---"
        )
        hazir_metinler.append(tek_metin)
        
    print("🚀 Türkçe yapay zeka vektör haritası çıkarılıyor (Embedding)...")
    embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small")
    
    # Vektör veritabanını oluştur ve kaydet
    db = FAISS.from_texts(hazir_metinler, embeddings)
    db.save_local("faiss_mutfak_endeksi")
    print("\n✅ TEBRİKLER! Tüm yemekler 'faiss_mutfak_endeksi' veritabanına başarıyla aktarıldı!")

if __name__ == "__main__":
    json_veri_setini_islemle("recipes.json")