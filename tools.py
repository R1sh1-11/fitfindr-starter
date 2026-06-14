"""
tools.py
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to a .env file in the project root.")
    return Groq(api_key=api_key)


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    listings = load_listings()

    if max_price is not None:
        listings = [l for l in listings if l["price"] <= max_price]

    if size is not None:
        listings = [l for l in listings if size.lower() in l["size"].lower()]

    keywords = description.lower().split()

    def score(listing):
        searchable = " ".join([
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"]),
            " ".join(listing["colors"]),
            listing["brand"] or "",
        ]).lower()
        return sum(1 for kw in keywords if kw in searchable)

    scored = [(score(l), l) for l in listings]
    scored = [(s, l) for s, l in scored if s > 0]
    scored.sort(key=lambda x: x[0], reverse=True)

    return [l for _, l in scored]


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    client = _get_groq_client()

    item_desc = (
        f"{new_item['title']} ({new_item['category']}, "
        f"colors: {', '.join(new_item['colors'])}, "
        f"style: {', '.join(new_item['style_tags'])})"
    )

    if not wardrobe.get("items"):
        prompt = (
            f"I just thrifted this item: {item_desc}\n\n"
            "I don't have my wardrobe listed yet. Give me 1-2 outfit ideas "
            "for this piece based on its style. Suggest what types of bottoms, "
            "shoes, and outerwear would work well. Be specific and conversational, "
            "not like a product description."
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {item['name']} ({item['category']}, colors: {', '.join(item['colors'])})"
            for item in wardrobe["items"]
        )
        prompt = (
            f"I just thrifted this item: {item_desc}\n\n"
            f"Here's what I already own:\n{wardrobe_lines}\n\n"
            "Suggest 1-2 complete outfits using the new item paired with specific "
            "pieces from my wardrobe. Name each wardrobe piece you use. Be conversational "
            "and specific, like a friend giving style advice. No bullet points."
        )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate outfit suggestions right now. Error: {str(e)}"


def compare_price(item: dict) -> str:
    listings = load_listings()

    comparables = [
        l for l in listings
        if l["id"] != item["id"]
        and l["category"] == item["category"]
        and len(set(l["style_tags"]) & set(item["style_tags"])) >= 1
    ]

    if len(comparables) < 2:
        return "Not enough comparable listings to make a price comparison."

    avg = round(sum(l["price"] for l in comparables) / len(comparables), 2)
    item_price = item["price"]
    diff = item_price - avg

    if diff < -5:
        verdict = f"This is priced below average for similar items (avg ${avg}). Solid deal."
    elif diff > 10:
        verdict = f"This is priced above average for similar items (avg ${avg}). Worth checking condition closely."
    else:
        verdict = f"This is priced about average for similar items (avg ${avg}). Fair price."

    return f"Compared {len(comparables)} similar listings. Average price: ${avg}. {verdict}"


def create_fit_card(outfit: str, new_item: dict) -> str:
    if not outfit or not outfit.strip():
        return "No outfit to caption yet. Make sure an outfit suggestion was generated first."

    client = _get_groq_client()

    prompt = (
        f"Write a 2-3 sentence Instagram caption for this thrifted outfit.\n\n"
        f"The thrifted item: {new_item['title']}, ${new_item['price']} from {new_item['platform']}\n"
        f"The outfit: {outfit}\n\n"
        "Rules: casual and real, first person, mention the item name once, "
        "mention the price and platform once, capture the vibe. "
        "Sound like an actual person posting their OOTD, not a brand. No hashtags."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.95,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate a fit card right now. Error: {str(e)}"