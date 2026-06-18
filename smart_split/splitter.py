from decimal import Decimal, ROUND_HALF_UP


def to_units(value) -> int:
    return int(
        (Decimal(str(value or 0)) * 100).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def from_units(value: int) -> float:
    return float(Decimal(value) / Decimal(100))


def distribute_evenly(amount: int, people: list[str]) -> dict[str, int]:
    if not people:
        return {}
    sign = -1 if amount < 0 else 1
    absolute = abs(amount)
    quotient, remainder = divmod(absolute, len(people))
    return {
        person: sign * (quotient + (1 if index < remainder else 0))
        for index, person in enumerate(people)
    }


def distribute_proportionally(
    amount: int, weights: dict[str, int], people: list[str]
) -> dict[str, int]:
    if not people:
        return {}
    positive_weights = {person: max(0, weights.get(person, 0)) for person in people}
    total_weight = sum(positive_weights.values())
    if total_weight == 0:
        return distribute_evenly(amount, people)

    sign = -1 if amount < 0 else 1
    absolute = abs(amount)
    raw = {
        person: Decimal(absolute) * Decimal(weight) / Decimal(total_weight)
        for person, weight in positive_weights.items()
    }
    allocated = {person: int(value) for person, value in raw.items()}
    remainder = absolute - sum(allocated.values())
    order = sorted(
        people,
        key=lambda person: (raw[person] - allocated[person], -people.index(person)),
        reverse=True,
    )
    for person in order[:remainder]:
        allocated[person] += 1
    return {person: sign * allocated[person] for person in people}


def calculate_split(
    receipt: dict, participants: list[str], assignments: dict[str, list[str]]
) -> dict:
    people = {
        person: {"item_total_units": 0, "lines": []}
        for person in participants
    }

    for index, item in enumerate(receipt["items"]):
        selected = assignments.get(f"item_{index}", [])
        shares = distribute_evenly(to_units(item["total"]), selected)
        for person, amount in shares.items():
            people[person]["item_total_units"] += amount
            people[person]["lines"].append(
                {"label": item["name"], "amount_units": amount}
            )

    weights = {
        person: details["item_total_units"] for person, details in people.items()
    }
    for charge in receipt.get("charges", []):
        shares = distribute_proportionally(
            to_units(charge["amount"]), weights, participants
        )
        for person, amount in shares.items():
            people[person]["lines"].append(
                {"label": charge["name"], "amount_units": amount}
            )

    item_sum = sum(to_units(item["total"]) for item in receipt["items"])
    charge_sum = sum(to_units(charge["amount"]) for charge in receipt.get("charges", []))
    bill_total = to_units(receipt["total"])
    adjustment = bill_total - item_sum - charge_sum
    if adjustment:
        shares = distribute_proportionally(adjustment, weights, participants)
        for person, amount in shares.items():
            people[person]["lines"].append(
                {"label": "Penyesuaian bill", "amount_units": amount}
            )

    output_people = {}
    for person, details in people.items():
        total = sum(line["amount_units"] for line in details["lines"])
        output_people[person] = {
            "lines": [
                {"label": line["label"], "amount": from_units(line["amount_units"])}
                for line in details["lines"]
            ],
            "total": from_units(total),
        }

    allocated_total = sum(
        to_units(details["total"]) for details in output_people.values()
    )
    return {
        "people": output_people,
        "allocated_total": from_units(allocated_total),
        "bill_total": from_units(bill_total),
        "difference": from_units(bill_total - allocated_total),
        "is_balanced": allocated_total == bill_total,
    }


def format_idr(value) -> str:
    amount = Decimal(str(value or 0))
    if amount == amount.to_integral():
        formatted = f"{int(amount):,}".replace(",", ".")
    else:
        formatted = f"{amount:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"Rp{formatted}"

