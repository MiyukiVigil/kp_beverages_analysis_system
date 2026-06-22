def clean_data(raw):
    cleaned = []

    for item in raw:
        name = str(item.get("name", "")).strip()
        price = item.get("price", None)

        try:
            price = float(price) if price is not None else None
        except:
            price = None

        if name:
            cleaned.append({
                "name": name,
                "price": price
            })

    return cleaned