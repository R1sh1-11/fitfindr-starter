from tools import search_listings, suggest_outfit, create_fit_card, compare_price
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

def test_search_size_filter():
    results = search_listings("tee", size="L", max_price=None)
    assert all("l" in item["size"].lower() for item in results)

def test_suggest_outfit_empty_wardrobe():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    result = suggest_outfit(results[0], get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0

def test_suggest_outfit_with_wardrobe():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    result = suggest_outfit(results[0], get_example_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0

def test_create_fit_card_empty_outfit():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    result = create_fit_card("", results[0])
    assert "No outfit" in result

def test_create_fit_card_valid():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    result = create_fit_card("baggy jeans and chunky sneakers", results[0])
    assert isinstance(result, str)
    assert len(result) > 0

def test_compare_price_returns_string():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    result = compare_price(results[0])
    assert isinstance(result, str)
    assert len(result) > 0