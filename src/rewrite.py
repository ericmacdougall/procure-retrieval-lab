"""Cheap rule-based query rewriting: strip question boilerplate, drop quotes, expand abbreviations."""
import re

BOILER = [
    r"^what was the awarded value of the contract",
    r"^what is the combined awarded value of the",
    r"^how much was the",
    r"^what is the contract value for",
    r"^on what date did the",
    r"^on what date was the",
    r"^when does the contract",
    r"^which supplier won the",
    r"^which organisation bought the",
    r"^which contract notice covers this requirement:?",
    r"^which was awarded a higher value by",
    r"^which of the",
    r"^who was awarded the",
    r"^what was the",
    r"^which ",
    r"^what ",
    r"^who ",
]
TRAIL = [r"\b(worth|start|started earlier|end|awarded)\??$", r"\?$"]
ABBR = dict(
    nhs="national health service", dfe="department for education", la="local authority", hmrc="hm revenue and customs",
    ict="information and communications technology", it="information technology", fm="facilities management",
    hvac="heating ventilation and air conditioning", ppe="personal protective equipment", sen="special educational needs",
    mot="vehicle test", cctv="closed circuit television", wifi="wireless network", m_e="mechanical and electrical",
)


def rewrite(q):
    s = q.strip()
    low = s.lower()
    for p in BOILER:
        new = re.sub(p, "", low).strip()
        if new != low:
            low = new
            break
    for p in TRAIL:
        low = re.sub(p, "", low).strip()
    low = low.replace("'", " ").replace('"', " ")
    words = []
    for w in low.split():
        words.append(w)
        key = w.strip("(),.")
        if key in ABBR:
            words.append(ABBR[key])
    return " ".join(words)
