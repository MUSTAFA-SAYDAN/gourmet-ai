import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

app = FastAPI()

# CORS Ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- TELEFON VE TARAYICI İÇİN SAYFA YÖNLENDİRMELERİ ---
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
# -----------------------------------------------------

# 🔑 GROQ API BAĞLANTISI
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# 🧠 DEV MODEL: Llama 3.3 70B
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.0,
    groq_api_key=GROQ_API_KEY
)

DATA_FILE = "saved_menu.txt"

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.txt'):
        raise HTTPException(status_code=400, detail="Lütfen sadece .txt dosyası yükleyin.")
    try:
        with open(DATA_FILE, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"status": "success", "message": "Tarif dosyası başarıyla bulut sistemine bağlandı!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask/")
async def ask_question(question: str):
    if not os.path.exists(DATA_FILE):
        raise HTTPException(status_code=400, detail="Sistemde tarif dosyası bulunamadı.")
        
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            context = f.read().strip()
            
        # 🎯 Profesyonel RAG Promptu
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "Sen sadece sana verilen BAĞLAM dökümanına göre cevap veren profesyonel bir mutfak robotusun.\n\n"
                "KATI KURALLAR:\n"
                "1. Sadece ve sadece dökümanda yazan bilgilere, malzemelere ve lezzet sırlarına sadık kal.\n"
                "2. Dökümanda açıkça yer almayan hiçbir malzemeyi veya pişirme yöntemini (fırın, salça, bulgur vb.) kafandan ekleme.\n"
                "3. Eğer sorulan soru dökümandaki tariflerde hiçbir şekilde geçmiyorsa, doğrudan 'Bu bilgi dökümanda yoktur.' de ve başka yorum yapma.\n"
                "4. Tüm cevaplarını sadece ve sadece akıcı, temiz bir Türkçe ile ver. Araya asla İngilizce kelimeler karıştırma."
            )),
            ("human", "BAĞLAM DÖKÜMANI:\n{context}\n\nSORU:\n{question}\n\nCEVAP:")
        ])
        
        chain = prompt | llm | StrOutputParser()
        response = chain.invoke({"context": context, "question": question})
        return {"answer": response.strip()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))