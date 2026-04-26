from llm_parser import extract_rules
from utils.cleaner import clean_llm_output
from utils.normalizer import normalize_rule
from utils.canonicalizer import canonicalize_rule
from utils.hasher import generate_rule_hash
from models.rule_model import Rule
from insert_rule import insert_rule
import psycopg2


def run_pipeline(text, regulator="UNKNOWN"):
    """Process text through full rule extraction and insertion pipeline."""
    rules = extract_rules(text)

    if not rules:
        print("❌ No rules extracted from text")
        return

    # Connect to database
    from config import DB_CONFIG
    conn = psycopg2.connect(**DB_CONFIG)

    for idx, rule_dict in enumerate(rules, start=1):
        try:
            print(f"\n--- Processing Rule {idx} ---")

            # Clean
            if isinstance(rule_dict, str):
                cleaned = clean_llm_output(rule_dict)
            else:
                cleaned = rule_dict

            # Normalize
            normalized = normalize_rule(cleaned)

            # Validate
            validated = Rule(**normalized)
            validated_dict = validated.model_dump()

            # Canonicalize
            canonical = canonicalize_rule(validated_dict)

            # Hash
            rule_hash = generate_rule_hash(canonical)

            # Insert
            cur = conn.cursor()
            insert_rule(cur, rule_hash, canonical)
            conn.commit()
            cur.close()

        except Exception as e:
            print(f"❌ Error processing rule {idx}: {e}")
            conn.rollback()
            continue

    conn.close()
    print(f"\n✓ Pipeline completed")