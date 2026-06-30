import hashlib
import io
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.chains import RetrievalQA
import openai
from pinecone import Pinecone

load_dotenv()

# --- CONFIGURAZIONE ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Ancora necessario per il modello di chat
REQUIRE_SECURE_TRANSPORT = os.getenv("REQUIRE_SECURE_TRANSPORT", "true").lower() == "true"

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

pinecone_client = Pinecone(api_key=PINECONE_API_KEY) if PINECONE_API_KEY else None

# --- MODELLI DATI ---
class ChatRequest(BaseModel):
    question: str = Field(..., description="Domanda dell'utente da processare.")
    namespace: str = Field(..., description="Namespace Pinecone da interrogare.")
    consent: bool = Field(..., description="Consenso esplicito al trattamento dei dati.")

    class Config:
        extra = "forbid"


class ErasureRequest(BaseModel):
    namespace: str = Field(..., description="Namespace Pinecone da cancellare.")
    consent: bool = Field(..., description="Consenso esplicito alla cancellazione dei dati.")

    class Config:
        extra = "forbid"

# --- INIZIALIZZAZIONE ---
app = FastAPI()


def _log_metadata(event: str, namespace: str | None = None) -> None:
    anonymized_namespace = "n/a"
    if namespace:
        anonymized_namespace = hashlib.sha256(namespace.encode()).hexdigest()[:12]
    print(f"[audit] event={event} namespace_hash={anonymized_namespace}")


def _ensure_consent(consent: bool) -> None:
    if not consent:
        raise HTTPException(status_code=403, detail="Consenso esplicito richiesto per proseguire.")


@app.middleware("http")
async def enforce_transport_security(request: Request, call_next):
    if REQUIRE_SECURE_TRANSPORT:
        forwarded_proto = request.headers.get("x-forwarded-proto")
        scheme = forwarded_proto or request.url.scheme
        if scheme != "https":
            return JSONResponse(
                status_code=400,
                content={"error": "Connessione non sicura: è richiesto HTTPS per il trattamento dei dati."},
            )

    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Modello di embedding gratuito
print("Caricamento del modello di embedding HuggingFace...")
embeddings = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-large",
    encode_kwargs={"normalize_embeddings": True}
)
print("Modello di embedding caricato.")

# Modello di chat (continuiamo a usare OpenAI per il ragionamento)
llm = ChatOpenAI(model_name="gpt-4", temperature=0)

# --- ENDPOINTS ---
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Benvenuto nel backend dell'assistente AI!"}

@app.post("/api/chat")
def chat(request: ChatRequest):
    _ensure_consent(request.consent)
    _log_metadata(event="chat_request", namespace=request.namespace)

    if not PINECONE_API_KEY:
        return {"error": "PINECONE_API_KEY non è configurata nel file .env"}
    if not PINECONE_INDEX_NAME:
        return {"error": "PINECONE_INDEX_NAME non è configurato nel file .env"}

    vectorstore = PineconeVectorStore.from_existing_index(
        index_name=PINECONE_INDEX_NAME,
        embedding=embeddings,
        namespace=request.namespace
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever()
    )

    try:
        response = qa_chain.invoke({"query": request.question})
        return {"answer": response.get("result")}
    except Exception as e:
        print(f"Errore durante l'esecuzione della chain (namespace hash): {hashlib.sha256(request.namespace.encode()).hexdigest()[:12]} | {e}")
        return {"error": "Si è verificato un errore nel processare la richiesta."}


@app.post("/api/voice-search")
async def voice_search(
    file: UploadFile = File(...),
    language: str = Form("it"),
    consent: bool = Form(...),
):
    _ensure_consent(consent)
    _log_metadata(event="voice_search")

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY non è configurata.")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Il file audio è vuoto.")

    audio_stream = io.BytesIO(audio_bytes)
    audio_stream.name = Path(file.filename or "audio.webm").name

    try:
        response = openai.Audio.transcribe(
            model="gpt-4o-mini-transcribe",
            file=audio_stream,
            language=(language or "it").strip() or "it",
        )
    except Exception as exc:
        print(f"Errore nella trascrizione vocale: {exc}")
        raise HTTPException(status_code=500, detail="Errore durante la trascrizione vocale.") from exc

    transcript = ""
    if isinstance(response, dict):
        transcript = response.get("text") or response.get("transcript") or ""
    else:
        transcript = getattr(response, "text", "") or getattr(response, "transcript", "")

    transcript = (transcript or "").strip()
    return {"query": transcript}


@app.post("/api/erase-namespace")
def erase_namespace(request: ErasureRequest):
    _ensure_consent(request.consent)
    _log_metadata(event="erase_namespace", namespace=request.namespace)

    if not pinecone_client or not PINECONE_INDEX_NAME:
        raise HTTPException(status_code=500, detail="Pinecone non è configurato correttamente.")

    try:
        index = pinecone_client.Index(PINECONE_INDEX_NAME)
        index.delete(delete_all=True, namespace=request.namespace)
    except Exception as exc:
        namespace_hash = hashlib.sha256(request.namespace.encode()).hexdigest()[:12]
        print(f"Errore nella cancellazione del namespace hash={namespace_hash}: {exc}")
        raise HTTPException(status_code=500, detail="Errore durante la cancellazione dei dati.") from exc

    return {"status": "erased", "namespace": request.namespace}
