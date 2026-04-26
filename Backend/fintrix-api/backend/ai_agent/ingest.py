import os
from pathlib import Path
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
from rank_bm25 import BM25Okapi

from backend.ai_agent.vector_store import save_vector_store

APP_ROOT = Path(__file__).resolve().parents[2]
PDF_FOLDER = APP_ROOT / "regulations"

model = SentenceTransformer("all-MiniLM-L6-v2")

texts = []
metadata = []


def chunk_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        if len(chunk.strip()) > 150:
            chunks.append(chunk.strip())

        start += chunk_size - overlap

    return chunks


for file in os.listdir(PDF_FOLDER):

    if file.endswith(".pdf"):

        path = PDF_FOLDER / file
        reader = PdfReader(path)

        for page_number, page in enumerate(reader.pages):

            text = page.extract_text()

            if not text:
                continue

            # clean text
            text = text.replace("\n", " ")
            text = " ".join(text.split())

            chunks = chunk_text(text)

            for chunk in chunks:
                texts.append(chunk)

                metadata.append({
                    "source": file,
                    "page": page_number + 1
                })


# embeddings
embeddings = model.encode(texts)

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

# BM25 tokens
tokenized_texts = [text.lower().split() for text in texts]

# save everything
save_vector_store(index, texts, metadata, tokenized_texts)

print("Documents ingested successfully.")
