# FitFindr

A multi-tool AI agent that helps users find secondhand clothing and figure out how to wear it. The agent searches mock thrift listings, suggests outfits based on your wardrobe, generates a shareable fit card caption, and checks whether the price is fair.

---

## Tool Inventory

### search_listings(description, size, max_price)
Filters the listings dataset by keyword relevance, size, and price ceiling. Scores each listing by how many description keywords appear in its title, description, style_tags, category, and colors. Returns a list of matching listing dicts sorted by score, highest first. Returns an empty list if nothing matches.

Each result contains: id (str), title (str), description (str), category (str), style_tags (list), size (str), condition (str), price (float), colors (list), brand (str or None), platform (str).

### suggest_outfit(new_item, wardrobe)
Calls the Groq LLM with the thrifted item and the user's wardrobe to generate 1-2 outfit combinations. If the wardrobe is empty, the LLM is prompted for general styling advice based on the item's style tags instead. Returns a non-empty string in both cases.

### create_fit_card(outfit, new_item)
Calls the Groq LLM to generate a 2-3 sentence Instagram-style caption referencing the item name, price, platform, and overall outfit vibe. Temperature is set to 0.95 so output varies across calls. Returns an error string if outfit is empty without calling the LLM.

### compare_price(item)
Finds comparable listings in the dataset by matching on category and overlapping style_tags. Calculates the average price and returns a plain-language assessment. Returns a fallback string if fewer than 2 comparables are found.

---

## How the Planning Loop Works

After the user submits a query, the agent parses it with regex to extract a description, size, and max_price. It calls search_listings with those parameters.

If search_listings returns empty and a size was parsed, the agent retries with size=None and tells the user the size filter was removed. If results are still empty, the agent sets session["error"] and returns early without calling any LLM tools.

If results are found, the agent sets session["selected_item"] to the top result and calls suggest_outfit. The outfit suggestion flows directly into create_fit_card. Then compare_price runs on the selected item. All four results are stored in the session dict and returned together.

The agent never calls suggest_outfit or create_fit_card when search_listings returns nothing.

---

## State Management

A single session dict is created at the start of each run_agent() call and passed through every step. Tools do not re-receive input from the user. Each tool reads its inputs from the session dict populated by the previous step.

Keys tracked:
- `parsed`: extracted description, size, max_price, and size_removed flag
- `search_results`: full list returned by search_listings
- `selected_item`: results[0], passed into suggest_outfit and create_fit_card
- `outfit_suggestion`: string from suggest_outfit, passed into create_fit_card
- `fit_card`: string from create_fit_card
- `price_assessment`: string from compare_price
- `error`: set on early termination, None on success

---

## Error Handling

**search_listings:** If no results match, the agent returns: "No listings matched your search. Try a broader description, remove the size filter, or raise your price limit." If a size was provided and caused zero results, it retries once with size=None first and notes this in the output.

Example from testing:
query: "designer ballgown size XXS under $5"

Error: No listings matched your search. Try a broader description, remove the size filter, or raise your price limit.

**suggest_outfit:** If wardrobe["items"] is empty, the LLM is still called with a prompt asking for general styling advice based on the item's style_tags. It never raises an exception or returns an empty string.

Example from testing:
suggest_outfit(graphic_tee, empty_wardrobe)

→ "You scored a vintage graphic tee... pair it with high-waisted jeans and Vans..."

**create_fit_card:** If outfit is an empty string or None, returns "No outfit to caption yet. Make sure an outfit suggestion was generated first." without calling the LLM.

Example from testing:
create_fit_card("", listing)

→ "No outfit to caption yet. Make sure an outfit suggestion was generated first."

**compare_price:** If fewer than 2 comparable listings are found, returns "Not enough comparable listings to make a price comparison."

---

## Spec Reflection

The planning.md spec helped most during the planning loop implementation. Having the exact conditional branches written out (check empty results, retry with size=None, return early) made it straightforward to implement run_agent() without second-guessing the logic mid-code.

One divergence: the spec described storing a size_removed boolean as a separate session key. In the implementation it ended up nested inside session["parsed"] as session["parsed"]["size_removed"] since it's metadata about the parse step, not a tool result. This made more sense structurally and did not affect any downstream tool calls.

---

## AI Usage

**Tool implementations:** I gave Claude the planning.md spec for each tool (inputs, return value, failure mode) and the listings.json field list, and asked it to implement each function one at a time. Before running the generated code I checked that search_listings filtered on all three parameters and returned an empty list rather than raising on no matches, that suggest_outfit handled empty wardrobe["items"] with a fallback prompt, and that create_fit_card guarded the empty outfit case before calling the LLM. I ran the failure-mode tests for each tool before moving on.

**Planning loop:** I gave Claude the architecture diagram and the Planning Loop and State Management sections from planning.md and asked it to implement run_agent(). I reviewed the output and added the retry-with-loosened-size logic myself since the generated code only handled the single-attempt case. I also moved size_removed into session["parsed"] rather than a top-level key as the generated code had it.

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Add your Groq API key to a `.env` file:
GROQ_API_KEY=your_key_here

Run the app:
```bash
python app.py
```

Run tests:
```bash
python -m pytest tests/ -v
```