from pathlib import Path
import faiss
import pickle

AI_AGENT_DIR = Path(__file__).resolve().parent
VECTOR_PATH = AI_AGENT_DIR / "vector.index"
TEXT_PATH = AI_AGENT_DIR / "texts.pkl"
META_PATH = AI_AGENT_DIR / "metadata.pkl"
TOKEN_PATH = AI_AGENT_DIR / "tokens.pkl"


def save_vector_store(index, texts, metadata, tokenized_texts):
    faiss.write_index(index, str(VECTOR_PATH))

    with open(TEXT_PATH, "wb") as f:
        pickle.dump(texts, f)

    with open(META_PATH, "wb") as f:
        pickle.dump(metadata, f)

    with open(TOKEN_PATH, "wb") as f:
        pickle.dump(tokenized_texts, f)


def load_vector_store():
    if not VECTOR_PATH.exists() or not TEXT_PATH.exists() or not META_PATH.exists() or not TOKEN_PATH.exists():
        raise FileNotFoundError("Vector store files are missing. Re-run ai_agent/ingest.py to rebuild.")
    index = faiss.read_index(str(VECTOR_PATH))

    with open(TEXT_PATH, "rb") as f:
        texts = pickle.load(f)

    with open(META_PATH, "rb") as f:
        metadata = pickle.load(f)

    with open(TOKEN_PATH, "rb") as f:
        tokenized_texts = pickle.load(f)

    return index, texts, metadata, tokenized_texts
