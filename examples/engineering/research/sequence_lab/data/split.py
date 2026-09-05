def split_records(rows):
    result = {name: [row for row in rows if row["split"] == name] for name in ("train", "validation", "adapt")}
    if any(not subset for subset in result.values()):
        raise ValueError("every declared split needs records")
    return result
