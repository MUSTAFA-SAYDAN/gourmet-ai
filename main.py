import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

app = FastAPI()

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

# Groq ve Vektör Bağlantıları
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.0,
    groq_api_key=GROQ_API_KEY
)

# FAISS Vektör İndeksini Yükle
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = FAISS.load_local("faiss_mutfak_endeksi", embeddings, allow_dangerous_deserialization=True)

@app.post("/ask/")
async def ask_question(question: str):
    try:
        # Sorulan soruyla ilgili SADECE en alakalı 1 tarifi çek
        docs = vectorstore.similarity_search(question, k=1)
        if not docs:
            return {"answer": "Üzgünüm, aradığınız tarif dökümanda bulunamadı."}
            
        context = docs[0].page_content
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "Sen sadece sana verilen BAĞLAM dökümanına göre cevap veren profesyonel bir mutfak robotusun.\n\n"
                "KATI KURALLAR:\n"
                "1. Sadece ve sadece dökümanda yazan bilgilere, malzemelere ve lezzet sırlarına sadık kal.\n"
                "2. Dökümanda açıkça yer almayan hiçbir malzemeyi veya pişirme yöntemini kafandan ekleme.\n"
                "3. Eğer sorulan soru dökümandaki tariflerde hiçbir şekilde geçmiyorsa, doğrudan 'Bu bilgi dökümanda yoktur.' de.\n"
                "4. Tüm cevaplarını sadece ve sadece akıcı, temiz bir Türkçe ile ver.\n"
                "5. TARİFLERİ ASLA ÖZETLEME! Dökümanda yer alan tüm yapılış adımlarını eksiksiz bir şekilde adım adım listele."
            )),
            ("human", "BAĞLAM DÖKÜMANI:\n{context}\n\nSORU:\n{question}\n\nCEVAP:")
        ])
        
        chain = prompt | llm | StrOutputParser()
        response = chain.invoke({"context": context, "question": question})
        return {"answer": response.strip()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))