from smart_split.splitter import calculate_split, distribute_evenly


def test_even_split_preserves_remainder():
    assert distribute_evenly(10000, ["A", "B", "C"]) == {
        "A": 3334,
        "B": 3333,
        "C": 3333,
    }


def test_complete_bill_is_exactly_balanced():
    receipt = {
        "items": [
            {"name": "Meal", "total": 100_000},
            {"name": "Drink", "total": 20_000},
        ],
        "charges": [
            {"name": "Tax", "amount": 12_000},
            {"name": "Service", "amount": 6_000},
        ],
        "total": 138_001,
    }
    assignments = {"item_0": ["A", "B", "C"], "item_1": ["A"]}

    result = calculate_split(receipt, ["A", "B", "C"], assignments)

    assert result["is_balanced"] is True
    assert result["allocated_total"] == 138_001
    assert sum(person["total"] for person in result["people"].values()) == 138_001


def test_negative_discount_is_allocated():
    receipt = {
        "items": [{"name": "Food", "total": 100_000}],
        "charges": [{"name": "Discount", "amount": -10_000}],
        "total": 90_000,
    }
    result = calculate_split(
        receipt, ["A", "B"], {"item_0": ["A", "B"]}
    )

    assert result["people"]["A"]["total"] == 45_000
    assert result["people"]["B"]["total"] == 45_000
    assert result["is_balanced"] is True

