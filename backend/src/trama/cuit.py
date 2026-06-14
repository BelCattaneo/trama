_MULTIPLIERS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def validate_cuit(value: str) -> bool:
    digits = value.replace("-", "")
    if len(digits) != 11 or not digits.isdigit():
        return False

    total = sum(int(d) * m for d, m in zip(digits[:10], _MULTIPLIERS, strict=True))
    remainder = 11 - (total % 11)

    # AFIP convention: remainder 11 → check digit 0; remainder 10 → CUIT invalid.
    if remainder == 11:
        check = 0
    elif remainder == 10:
        return False
    else:
        check = remainder

    return check == int(digits[10])
