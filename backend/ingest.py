import os
import argparse
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

def ingest_data(directory: str, company_id: str, structure_id: str):
    if not all([directory, company_id, structure_id, PINECONE_API_KEY, PINECONE_INDEX_NAME]):
        print("Errore: Assicurati che directory, company_id, structure_id e le variabili d'ambiente Pinecone siano impostate.")
        return

    namespace = f"{company_id}-{structure_id}"
    print(f"Inizio ingestione per il namespace: {namespace}")

    loader = DirectoryLoader(directory, glob="**/*.txt", loader_cls=TextLoader, show_progress=True)
    documents = loader.load()
    if not documents:
        print(f"Nessun documento .txt trovato nella directory: {directory}")
        return
    print(f"Caricati {len(documents)} documenti.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs_split = text_splitter.split_documents(documents)
    print(f"Documenti suddivisi in {len(docs_split)} chunks.")

    print("Inizializzazione del modello di embedding HuggingFace (potrebbe richiedere un download la prima volta)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large",
        encode_kwargs={"normalize_embeddings": True}
    )
    print("Modello di embedding caricato.")

    print(f"Caricamento dei chunks sull'indice '{PINECONE_INDEX_NAME}'...")

    PineconeVectorStore.from_documents(
        documents=docs_split,
        embedding=embeddings,
        index_name=PINECONE_INDEX_NAME,
        namespace=namespace
    )

    print(f"Ingestione completata con successo per il namespace: {namespace}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carica i dati su Pinecone in un namespace specifico.")
    parser.add_argument("--dir", type=str, required=True, help="La directory contenente i documenti da caricare.")
    parser.add_argument("--company", type=str, required=True, help="L'ID della società.")
    parser.add_argument("--structure", type=str, required=True, help="L'ID della struttura.")

    args = parser.parse_args()

    ingest_data(args.dir, args.company, args.structure)