import re
import json

def clean_llm_output(text: str):
    # Remove ```json ... ```
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)

    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON from LLM")

    # If it's a list → take first rule (for now)
    if isinstance(data, list):
        data = data[0]

    return data