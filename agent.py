"""
agent.py
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card, compare_price


def _new_session(query: str, wardrobe: dict) -> dict:
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "price_assessment": None,
        "error": None,
    }


def _parse_query(query: str) -> dict:
    q = query.lower()

    # extract max_price
    price_match = re.search(r"under\s*\$?(\d+\.?\d*)", q)
    max_price = float(price_match.group(1)) if price_match else None

    # extract size
    size_match = re.search(
        r"\bsize\s*([a-z0-9/]+)\b|"
        r"\b(xxs|xs|s/m|m/l|l/xl|xs|s|m|l|xl|xxl)\b|"
        r"\b(w\d{2})\b",
        q
    )
    size = None
    if size_match:
        size = next(g for g in size_match.groups() if g is not None).upper()

    # description: strip price and size phrases, keep the rest
    description = re.sub(r"under\s*\$?\d+\.?\d*", "", q)
    description = re.sub(r"\bsize\s*[a-z0-9/]+\b", "", description)
    description = re.sub(r"\b(xxs|xs|s/m|m/l|l/xl|xs|s|m|l|xl|xxl|w\d{2})\b", "", description)
    description = re.sub(r"[^\w\s]", " ", description).strip()

    return {"description": description, "size": size, "max_price": max_price}


def run_agent(query: str, wardrobe: dict) -> dict:
    session = _new_session(query, wardrobe)

    # Step 2: parse query
    parsed = _parse_query(query)
    session["parsed"] = parsed

    # Step 3: search
    results = search_listings(
        description=parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = results

    # retry with loosened size constraint if no results
    if not results and parsed["size"] is not None:
        results = search_listings(
            description=parsed["description"],
            size=None,
            max_price=parsed["max_price"],
        )
        if results:
            session["search_results"] = results
            session["parsed"]["size_removed"] = True

    if not results:
        session["error"] = (
            "No listings matched your search. Try a broader description, "
            "remove the size filter, or raise your price limit."
        )
        return session

    # Step 4: select top result
    session["selected_item"] = results[0]

    # Step 5: suggest outfit
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"],
        wardrobe,
    )

    # Step 6: fit card
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"],
        session["selected_item"],
    )

    # Step 7: price comparison (stretch)
    session["price_assessment"] = compare_price(session["selected_item"])

    return session


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")
        print(f"\nPrice: {session['price_assessment']}")
        if session["parsed"].get("size_removed"):
            print("\n(Note: size filter was removed to find results)")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")