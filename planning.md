# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

### Tool 1: search_listings

**What it does:**
Filters the listings dataset and returns items that match the user's description, size, and price ceiling. Matching is done against the title, description, style_tags, category, and colors fields.

**Input parameters:**
- `description` (str): A plain-language description of what the user is looking for (e.g. "vintage graphic tee")
- `size` (str): The user's size as a string (e.g. "M", "W28"); if None, size is not filtered
- `max_price` (float): The highest price the user is willing to pay; if None, price is not filtered

**What it returns:**
A list of dicts, where each dict is a listing from listings.json containing: id (str), title (str), description (str), category (str), style_tags (list of str), size (str), condition (str), price (float), colors (list of str), brand (str or null), and platform (str). Returns an empty list if no listings match.

**What happens if it fails or returns nothing:**
The agent stores an error message in session["error"] explaining that no listings matched and suggests the user try a broader description, remove the size filter, or raise the price limit. The agent returns early and does not call suggest_outfit or create_fit_card.

---

### Tool 2: suggest_outfit

**What it does:**
Takes a specific listing and the user's wardrobe, then calls the LLM to generate one or more complete outfit combinations using the new item paired with things from the wardrobe.

**Input parameters:**
- `new_item` (dict): A single listing dict returned by search_listings, containing at minimum title, category, style_tags, and colors
- `wardrobe` (dict): The user's wardrobe in the schema format, with an "items" key containing a list of wardrobe item dicts (each with id, name, category, colors, style_tags, and optional notes)

**What it returns:**
A string containing one or more outfit suggestions written in plain conversational language. Each suggestion names specific wardrobe items by name and explains the styling reasoning.

**What happens if it fails or returns nothing:**
If wardrobe["items"] is empty, the LLM is still called but prompted to give general styling advice for the item based on its style_tags alone, without referencing any specific wardrobe pieces. If the LLM call fails, the agent returns a fallback string: "Could not generate outfit suggestions right now. Try again or describe your wardrobe manually."

---

### Tool 3: create_fit_card

**What it does:**
Takes a complete outfit suggestion and the new item, then calls the LLM to generate a short shareable caption in the style of an Instagram or Depop post.

**Input parameters:**
- `outfit` (str): The outfit suggestion string returned by suggest_outfit
- `new_item` (dict): The listing dict for the thrifted item being featured

**What it returns:**
A string of 1 to 3 sentences written in casual, first-person social media voice. It references the specific item, its price, the platform it came from, and the overall look. Output varies each call due to LLM temperature.

**What happens if it fails or returns nothing:**
If outfit is an empty string or None, the tool returns the string: "No outfit to caption yet. Make sure an outfit suggestion was generated first." If the LLM call fails, the tool returns: "Could not generate a fit card right now."

---

### Additional Tools

### Tool 4: compare_price

**What it does:**
Given a listing, finds comparable items in the dataset by matching on category and overlapping style_tags, then calculates the average price of those comparables and returns a plain-language assessment of whether the item is priced well.

**Input parameters:**
- `item` (dict): A single listing dict containing at minimum category (str), style_tags (list of str), and price (float)

**What it returns:**
A dict with three keys: comparable_count (int, how many similar items were found), average_comparable_price (float, rounded to 2 decimal places), and assessment (str, a plain-language verdict like "This is priced below average for similar items" or "This is slightly above average but in line with the condition").

**What happens if it fails or returns nothing:**
If fewer than 2 comparable items are found, the tool returns: "Not enough comparable listings to make a price comparison."

---

## Planning Loop

After receiving the user query, the agent calls search_listings with the parsed description, size, and max_price.

If search_listings returns an empty list, the agent checks whether the size parameter was set. If size was set, it retries search_listings once with size=None and tells the user the size filter was removed. If the retry also returns empty, or if size was already None, the agent sets session["error"] and returns early without calling any further tools.

If search_listings returns results, the agent sets session["selected_item"] = results[0] (the first result) and calls suggest_outfit with that item and the provided wardrobe.

If suggest_outfit returns a non-empty string, the agent sets session["outfit_suggestion"] and calls create_fit_card with the outfit string and the selected item.

If the agent has session["selected_item"] set, it also calls compare_price on that item and stores the result in session["price_assessment"].

The agent is done when create_fit_card returns and all four session keys are populated, or when an error causes an early return.

---

## State Management

The agent uses a single session dict that is created at the start of run_agent() and passed through each step. The keys are:

- `selected_item`: set after search_listings returns results; passed directly into suggest_outfit and create_fit_card
- `outfit_suggestion`: set after suggest_outfit returns; passed directly into create_fit_card
- `fit_card`: set after create_fit_card returns
- `price_assessment`: set after compare_price returns
- `error`: set if any tool fails or returns nothing; causes early return

No tool re-receives data from the user. Every tool after search_listings reads its inputs from the session dict, not from new user input.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | If size was set, retry with size=None and tell the user "No results for that size. Showing results for all sizes instead." If still empty, tell the user "Nothing matched that search. Try a broader description or a higher price limit." Return early. |
| suggest_outfit | Wardrobe is empty | Call the LLM anyway with a prompt that asks for general styling advice based on the item's style_tags, without referencing any wardrobe items. Return that advice as the outfit suggestion. |
| create_fit_card | Outfit input is empty or None | Return the string "No outfit to caption yet. Make sure an outfit suggestion was generated first." without calling the LLM. |
| compare_price | Fewer than 2 comparable listings found | Return the string "Not enough comparable listings to make a price comparison." |

---

## Architecture
User query (description, size, max_price, wardrobe)

|

v

Planning Loop

|

v

search_listings(description, size, max_price)

|

|-- results = [] AND size was set

|       |

|       v

|   retry: search_listings(description, size=None, max_price)

|       |

|       |-- still empty --> session["error"] = "Nothing matched..." --> return session

|       |

|       |-- results found --> session["selected_item"] = results[0]

|

|-- results = [] AND size was None --> session["error"] = "Nothing matched..." --> return session

|

|-- results found --> session["selected_item"] = results[0]

|

v

suggest_outfit(session["selected_item"], wardrobe)

|

|-- wardrobe is empty --> LLM called with general styling prompt (no wardrobe items)

|

|-- wardrobe has items --> LLM called with full wardrobe context

|

v

session["outfit_suggestion"] = result

|

v

create_fit_card(session["outfit_suggestion"], session["selected_item"])

|

|-- outfit is empty --> return error string, skip LLM call

|

v

session["fit_card"] = result

|

v

compare_price(session["selected_item"])

|

|-- fewer than 2 comparables --> session["price_assessment"] = "Not enough data..."

|

v

session["price_assessment"] = result

|

v

return session
---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

For search_listings, I will give Claude the Tool 1 spec block from this file (inputs, return value, failure mode) and the listings.json field list, and ask it to implement the function using load_listings() from utils/data_loader.py. I will verify the output filters on all three parameters, handles None for size and max_price, and returns an empty list (not an exception) when nothing matches. I will test it with three queries: one that should return results, one with an impossible price, and one with a size that does not exist in the data.

For suggest_outfit, I will give Claude the Tool 2 spec block and the wardrobe schema, and ask it to implement the function calling Groq llama-3.3-70b-versatile. I will check that it handles empty wardrobe["items"] with a fallback prompt rather than crashing, and that the returned string actually names wardrobe pieces when the wardrobe is populated.

For create_fit_card, I will give Claude the Tool 3 spec block and ask it to implement the function with a temperature of 0.9 or higher so outputs vary. I will run it three times on the same input and confirm the outputs differ. I will check that passing an empty outfit string returns the error string and does not call the LLM.

For compare_price, I will give Claude the Tool 4 spec block and the listings.json field list, and ask it to implement the function using load_listings(). I will verify it matches on category and style_tags overlap (not exact match), returns a dict with the three specified keys, and handles the low-comparables case without throwing an error.

**Milestone 4 — Planning loop and state management:**

I will give Claude the full Architecture diagram and the Planning Loop and State Management sections from this file and ask it to implement run_agent() in agent.py. I will verify the generated code branches on whether search_listings returns an empty list before calling suggest_outfit, stores values in the session dict between calls rather than using local variables, and includes the retry-with-loosened-constraints logic for the size filter. I will test it by running the agent with an impossible query and confirming it returns session["error"] without calling the LLM tools.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent calls search_listings("vintage graphic tee", size=None, max_price=30.0). The function loads listings.json and filters for items whose title, description, style_tags, or category contain terms matching the description and whose price is at or below 30.0. It returns two matches: lst_006 (Graphic Tee, 2003 Tour Bootleg Style, $24, depop) and lst_033 (Vintage Band Tee, Faded Grey, $19, depop). The agent sets session["selected_item"] = lst_006.

**Step 2:**
The agent calls suggest_outfit(session["selected_item"], example_wardrobe). The new item is lst_006: a boxy black graphic tee with style_tags ["graphic tee", "vintage", "grunge", "streetwear", "band tee"]. The wardrobe contains baggy dark-wash jeans (w_001), chunky white sneakers (w_007), and a vintage black denim jacket (w_006) among others. The LLM returns: "Pair the graphic tee with your baggy dark-wash jeans and chunky white sneakers for a clean 90s streetwear look. Throw the black denim jacket over it if you want some structure. Tuck the front corner of the tee into the waistband to break up the silhouette." The agent sets session["outfit_suggestion"] to that string.

**Step 3:**
The agent calls create_fit_card(session["outfit_suggestion"], session["selected_item"]). The LLM generates a short caption referencing the item, price, and platform. The agent sets session["fit_card"] to the result.

**Step 4:**
The agent calls compare_price(session["selected_item"]). It finds listings in the same category (tops) with overlapping style_tags like "graphic tee", "vintage", and "streetwear". It calculates the average price of comparables and returns an assessment. The agent sets session["price_assessment"] to the result.

**Final output to user:**
The Gradio interface shows four panels: the top search result (title, price, condition, platform), the outfit suggestion paragraph, the fit card caption, and the price comparison assessment. The user sees everything in one view without having to re-enter any information between steps.