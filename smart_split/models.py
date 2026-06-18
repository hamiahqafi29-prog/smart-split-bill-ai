from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def _money(value) -> float:
    try:
        return float(Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        return 0.0


def _number(value, default=1.0) -> float:
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return default


def empty_receipt() -> dict:
    return {
        "merchant": "",
        "items": [],
        "subtotal": 0.0,
        "charges": [],
        "total": 0.0,
    }


def normalize_receipt(data: dict) -> dict:
    result = empty_receipt()
    result["merchant"] = str(data.get("merchant") or "")

    for raw in data.get("items") or []:
        quantity = _number(raw.get("quantity"), 1.0)
        unit_price = _money(raw.get("unit_price"))
        total = _money(raw.get("total"))
        if not total and quantity and unit_price:
            total = _money(quantity * unit_price)
        result["items"].append(
            {
                "name": str(raw.get("name") or "Item").strip(),
                "quantity": quantity,
                "unit_price": unit_price,
                "total": total,
            }
        )

    result["subtotal"] = _money(data.get("subtotal"))
    if not result["subtotal"]:
        result["subtotal"] = _money(sum(item["total"] for item in result["items"]))

    for raw in data.get("charges") or []:
        result["charges"].append(
            {
                "name": str(raw.get("name") or "Biaya tambahan").strip(),
                "amount": _money(raw.get("amount")),
            }
        )

    result["total"] = _money(data.get("total"))
    if not result["total"]:
        result["total"] = _money(
            result["subtotal"] + sum(charge["amount"] for charge in result["charges"])
        )
    return result


def validate_receipt(receipt: dict) -> list[str]:
    warnings = []
    item_sum = _money(sum(item.get("total", 0) for item in receipt.get("items", [])))
    subtotal = _money(receipt.get("subtotal"))
    charge_sum = _money(
        sum(charge.get("amount", 0) for charge in receipt.get("charges", []))
    )
    total = _money(receipt.get("total"))

    if item_sum != subtotal:
        warnings.append(
            f"Jumlah total item ({item_sum:.2f}) tidak sama dengan subtotal "
            f"({subtotal:.2f})."
        )
    expected_total = _money(subtotal + charge_sum)
    if expected_total != total:
        warnings.append(
            f"Subtotal + biaya tambahan ({expected_total:.2f}) tidak sama "
            f"dengan total bill ({total:.2f})."
        )
    return warnings
