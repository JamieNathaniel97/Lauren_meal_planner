"""Normalise free-text ingredient names to a matching key (shared by importers).

Only words that never change what an ingredient is are removed ("finely",
"large", "for serving"). Words like "ground", "dried", "crushed", "smoked"
or "hot" stay, because ground coriander isn't fresh coriander and crushed
red pepper isn't a bell pepper. Matching then looks for the longest known
phrase inside the name, so "minced garlic" still finds "garlic".
"""
import re
import unicodedata

PREP = ("fresh|freshly|finely|roughly|coarsely|thinly|thickly|very|diced|sliced|grated|large|small|"
        "medium|ripe|peeled|seeded|deseeded|trimmed|halved|quartered|cubed|shredded|torn|picked|rinsed|"
        "drained|soaked|softened|melted|beaten|room|temperature|good|quality|best|plus|more|for|to|taste|"
        "serving|serve|garnish|optional|about|approx|organic|unsalted|pitted|raw|boneless|"
        "skinless")
PREP_RE = re.compile(rf"\b(?:{PREP})\b")


def norm(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\([^)]*\)", " ", s)          # drop (notes)
    s = s.split(",")[0].split(";")[0]          # drop ", sliced"
    s = re.sub(r"\b(?:for|the)\b.*$", " ", s)  # "oil for frying", "eggs (the cream)"
    s = s.replace("-", " ").replace("/", " or ")
    s = PREP_RE.sub(" ", s)
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()
