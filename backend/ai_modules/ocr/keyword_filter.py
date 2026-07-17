import json
import re
from typing import List

from ai_modules.utils.llm_client import chat_completion

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "your",
    "have",
    "will",
    "about",
    "there",
    "their",
    "while",
    "where",
    "which",
    "when",
    "were",
    "been",
    "being",
    "also",
    "just",
    "more",
    "some",
    "such",
    "than",
    "then",
    "them",
    "they",
    "over",
    "under",
    "very",
    "much",
    "onto",
}


def _normalize_keyword(keyword: str) -> str:
    return re.sub(r"\s+", " ", str(keyword or "")).strip(" -_,.;:()[]{}")


def _is_useful_keyword(keyword: str) -> bool:
    lowered = keyword.lower()
    if not lowered:
        return False
    if lowered in STOPWORDS:
        return False
    if len(lowered) <= 2 and not keyword.isupper():
        return False
    if not re.search(r"[a-zA-Z]", keyword):
        return False
    if len(set(re.findall(r"[a-zA-Z]", lowered))) == 1 and len(lowered) > 3:
        return False
    return True


def _local_filter(keywords: List[str]) -> List[str]:
    filtered = []
    seen = set()

    for keyword in keywords:
        cleaned = _normalize_keyword(keyword)
        key = cleaned.lower()
        if not _is_useful_keyword(cleaned):
            continue
        if key in seen:
            continue
        seen.add(key)
        filtered.append(cleaned)

    return filtered


def build_prompt(input_text: str) -> str:
    return f"""
You are an intelligent meeting assistant.

Task:
Filter and refine keywords.

Rules:
- Return ONLY JSON
- Format: {{"keywords": ["keyword1", "keyword2"]}}
- Remove duplicates
- Keep important short terms like AI, ML, US
- Remove irrelevant or noisy words

Keywords:
{input_text}
"""


def parse_response(content: str, fallback: List[str]) -> List[str]:
    try:
        return list(set(json.loads(content).get("keywords", fallback)))
    except Exception:
        match = re.search(r"\{.*?\}", content, re.DOTALL)
        if not match:
            return fallback
        try:
            return list(set(json.loads(match.group()).get("keywords", fallback)))
        except Exception:
            return fallback


def filter_keywords(keywords: List[str]) -> List[str]:
    if not keywords:
        return []

    fallback = _local_filter(keywords)
    if not fallback:
        return []

    try:
        content = chat_completion(
            [
                {"role": "system", "content": "Return only JSON."},
                {"role": "user", "content": build_prompt("\n".join(fallback))},
            ],
            temperature=0,
            max_tokens=300,
        )
        return _local_filter(parse_response(content, fallback))
    except Exception as exc:
        print(f"LLM keyword filter unavailable, using local filter: {exc}")
        return fallback
