# 👨‍🍳 GourmetAI - Dijital Şef Asistanı

GourmetAI; mutfakta ne pişireceğine karar veremeyenler, elindeki malzemeleri değerlendirmek isteyenler veya pratik tarifler arayanlar için geliştirilmiş yapay zeka destekli, sesli etkileşimli ve PWA uyumlu bir dijital şef asistanıdır.

![GourmetAI Preview](https://img.shields.io/badge/GourmetAI-v1.0.0-orange?style=for-the-badge&logo=chef)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Groq API](https://img.shields.io/badge/Groq%20API-Powered-f39c12?style=for-the-badge)
![PWA](https://img.shields.io/badge/PWA-Supported-5A0FC8?style=for-the-badge&logo=pwa&logoColor=white)

---

## ✨ Öne Çıkan Özellikler

- 💬 **Akıllı Şef Sohbeti:** Groq API altyapısı ile hızlı, akıcı ve doğal Türkçe yemek tarifi önerileri.
- 🎙️ **Sesli Komut (Speech-to-Text):** Mutfakta elleriniz doluyken mikrofona basıp konuşarak tarif sorabilme.
- 🔊 **Sesli Tarif Okuma (Text-to-Speech):** Hazırlanan tarifleri sesli dinleme ve okumayı duraklatma / devam ettirme kontrolü.
- 📝 **Serbest Metinden Tarif Analizi:** Düz metin halindeki tarifleri yapay zekaya analiz ettirip veritabanına kaydetme.
- ❤️ **Favori Yönetimi:** Beğenilen tarifleri tek tıkla tarayıcı hafızasına (`LocalStorage`) kaydetme ve yönetme.
- 📱 **PWA (Progressive Web App) Desteği:** Mobil cihazlara ve masaüstüne uygulama olarak yüklenebilme (`manifest.json` & `sw.js`).
- ⚡ **Pratik Kategori Butonları:** *"15 Dakikalık Tarifler"*, *"Dolaptakilerle Yemek"*, *"Düşük Kalorili"* gibi tek tıkla soru sorma seçenekleri.

---

## 🛠️ Kullanılan Teknolojiler

### Backend
- **Python 3.x**
- **Groq API:** Yüksek hızlı yapay zeka model entegrasyonu.
- **JSON / TXT Veri Yapısı:** `recipes.json` ve `saved_menu.txt` ile tarif verisi yönetimi.

### Frontend
- **HTML5 & CSS3:** Modern, responsive ve kart tabanlı arayüz tasarımı.
- **Vanilla JavaScript (ES6+):** Asenkron `fetch` istekleri ve DOM yönetimi.
- **Marked.js:** Yapay zekadan gelen Markdown formatındaki yanıtları anında HTML'e dönüştürme.
- **Web Speech API:** Ses tanıma (`SpeechRecognition`) ve seslendirme (`SpeechSynthesisUtterance`).

---

## 📂 Proje Dizin Yapısı

```text
├── index.html          # Ana kullanıcı arayüzü ve istemci tarafı mantığı
├── process_kaggle.py   # Veri işleme ve API entegrasyon betikleri
├── recipes.json        # Yapılandırılmış tarif veritabanı
├── saved_menu.txt      # Kaydedilen menü içerikleri
├── requirements.txt   # Python bağımlılıkları
├── manifest.json       # PWA uygulama yapılandırma dosyası
└── sw.js               # Service Worker (Çevrimdışı/PWA desteği)
🚀 Kurulum ve Çalıştırma
1. Repoyu Klonlayın
Bash
git clone [https://github.com/KULLANICI_ADIN/GourmetAI.git](https://github.com/KULLANICI_ADIN/GourmetAI.git)
cd GourmetAI
2. Gerekli Paketleri Yükleyin
Bash
pip install -r requirements.txt
3. API Anahtarını Tanımlayın
.env dosyanıza veya çevre değişkenlerinize Groq API anahtarınızı ekleyin:

Bash
export GROQ_API_KEY="your_groq_api_key_here"
4. Uygulamayı Başlatın
Bash
python process_kaggle.py
Ardından tarayıcınızdan http://localhost:5000 adresine giderek Şef GourmetAI ile sohbet etmeye başlayabilirsiniz!

📄 Lisans
Bu proje MIT Lisansı ile lisanslanmıştır.
