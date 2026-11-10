"""Render a normalised document into field groups (head / body / terms) and plain text."""


def money(cur, x):
    return f"{cur} {x:,.2f}"


def fields(d):
    """Return list of (group, field, text). Field-aware chunking uses the groups."""
    sup = "; ".join(d["suppliers"])
    head = [
        ("head", "title", f"Title: {d['title']}"),
        ("head", "buyer", f"Buyer: {d['buyer']}"),
        ("head", "suppliers", f"Awarded to: {sup}"),
    ]
    desc = d.get("description") or ""
    body = [("body", "description", f"Description: {desc}" if desc else "Description: not provided")]
    if d["n_awards"] == 1:
        val = f"Awarded value: {money(d['currency'], d['amounts'][0])}"
    else:
        parts = ", ".join(money(d["currency"], a) for a in d["amounts"])
        val = f"Awarded values ({d['n_awards']} awards): {parts}. Total {money(d['currency'], d['total_value'])}"
    terms = [("terms", "value", val)]
    if d.get("award_date"):
        terms.append(("terms", "award_date", f"Award date: {d['award_date']}"))
    if d.get("contract_start"):
        terms.append(("terms", "contract_start", f"Contract start date: {d['contract_start']}"))
    if d.get("contract_end"):
        terms.append(("terms", "contract_end", f"Contract end date: {d['contract_end']}"))
    if d.get("category"):
        terms.append(("terms", "category", f"Category: {d['category']}"))
    if d.get("cpv_text"):
        terms.append(("terms", "cpv", f"Classification: {d['cpv_text']}"))
    if d.get("method"):
        terms.append(("terms", "method", f"Procedure: {d['method']}"))
    return head + body + terms


def doc_text(d):
    return chr(10).join(t for _, _, t in fields(d))
