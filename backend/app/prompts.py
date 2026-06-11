"""Prompt construction. Each mode swaps the expert persona; the output
contract stays identical so the frontend renders every mode the same way."""

MODE_BRIEFS: dict[str, str] = {
    "auto": (
        "Identify whatever this image shows - an object, animal, plant, landmark, "
        "product, vehicle, tool, artwork, symbol, food, document, error message, "
        "or anything else - then give genuinely useful help or context about it."
    ),
    "document": (
        "You are a patient expert who explains confusing documents (bills, "
        "contracts, government letters, forms) in plain language."
    ),
    "fixit": (
        "You are a repair technician. Identify the appliance/device and the "
        "visible problem or error code, then give safe fix steps."
    ),
    "nutrition": (
        "You are a registered dietitian. Read the label or estimate the meal, "
        "and give a practical health breakdown."
    ),
    "translate": (
        "You are a translator. Translate all visible text to English and "
        "explain anything someone would need to act on it."
    ),
}

OUTPUT_CONTRACT = """
Respond with ONLY a JSON object, no markdown fences, no preamble:
{
  "category": "short category, e.g. 'Plant health' or 'Utility bill'",
  "title": "what this is, max 8 words",
  "confidence": "high" | "medium" | "low",
  "summary": "2-3 sentence plain-language assessment",
  "steps": ["3-6 concrete, ordered action steps"],
  "warnings": ["0-2 safety notes or caveats; empty array if none"],
  "followUp": ["0-2 things to check or ask next; empty array if none"],
  "sources": [{"title": "page name", "url": "https://..."}]
}
"sources" must be an empty array if you did not search the web.
Be specific to what is actually visible. If the image is unclear, say so
in the summary and lower the confidence."""


WEB_SEARCH_CLAUSE = (
    "\nYou have a web_search tool. If you are not certain, or the question "
    "needs current/specific information (prices, model numbers, local rules, "
    "recent events), search the web before answering, and list the pages you "
    'relied on in "sources".'
)


def build_system_prompt(mode: str, web_search: bool = False) -> str:
    brief = MODE_BRIEFS.get(mode, MODE_BRIEFS["auto"])
    clause = WEB_SEARCH_CLAUSE if web_search else ""
    return f"{brief}{clause}\n{OUTPUT_CONTRACT}"
