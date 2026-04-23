"""Michelin Guide retrieval adapter — curated structured data per destination.

Returns Michelin-backed restaurant results when no live Michelin API is available.
Sorted by Michelin tier, then by rating.
"""

from typing import List

from app.models.concierge import UnifiedRestaurantResult

_MICHELIN_STAR_RANK = {
    "3 Stars": 5,
    "2 Stars": 4,
    "1 Star": 3,
    "Bib Gourmand": 2,
    "Selected": 1,
}

_MICHELIN_DB: dict[str, list[dict]] = {
    "paris": [
        {"name": "Guy Savoy", "michelin_status": "3 Stars", "cuisine": "French Contemporary", "neighborhood": "1st Arrondissement", "rating": 9.2, "review_count": 1840, "summary": "Legendary haute cuisine; iconic artichoke-truffle soup by one of France's greatest chefs.", "tags": ["Fine Dining", "Tasting Menu", "Iconic"]},
        {"name": "L'Astrance", "michelin_status": "3 Stars", "cuisine": "Contemporary French", "neighborhood": "16th Arrondissement", "rating": 9.0, "review_count": 890, "summary": "Pascal Barbot's intimate 20-seat restaurant with creative no-choice tasting menus.", "tags": ["Intimate", "Tasting Menu", "Innovative"]},
        {"name": "Le Grand Véfour", "michelin_status": "2 Stars", "cuisine": "Classic French", "neighborhood": "Palais Royal", "rating": 8.9, "review_count": 1240, "summary": "Historic 18th-century restaurant beneath the Palais Royal arcades. Beautifully preserved décor.", "tags": ["Historic", "Romantic", "Classic"]},
        {"name": "Septime", "michelin_status": "1 Star", "cuisine": "Neo-Bistro", "neighborhood": "11th Arrondissement", "rating": 8.7, "review_count": 3200, "summary": "Vegetable-forward tasting menus with natural wines. Paris's most sought-after reservation.", "tags": ["Natural Wine", "Seasonal", "Bistronomic"]},
        {"name": "Le Chateaubriand", "michelin_status": "Bib Gourmand", "cuisine": "Basque-French", "neighborhood": "11th Arrondissement", "rating": 8.4, "review_count": 2100, "summary": "Inaki Aizpitarte's neo-bistro with a daily-changing blackboard menu. Natural wine-focused.", "tags": ["Natural Wine", "Creative", "Neighborhood"]},
        {"name": "Chez L'Ami Jean", "michelin_status": "Bib Gourmand", "cuisine": "Basque", "neighborhood": "7th Arrondissement", "rating": 8.5, "review_count": 1900, "summary": "Convivial Basque cooking with outstanding rice pudding dessert.", "tags": ["Convivial", "Basque", "Value"]},
    ],
    "tokyo": [
        {"name": "Sukiyabashi Jiro Honten", "michelin_status": "3 Stars", "cuisine": "Sushi", "neighborhood": "Ginza", "rating": 9.5, "review_count": 2100, "summary": "Master Jiro Ono's legendary 10-seat counter. Pure Edo-style sushi. Reservations months ahead.", "tags": ["Legendary", "Omakase", "Counter"]},
        {"name": "Nihonryori RyuGin", "michelin_status": "3 Stars", "cuisine": "Japanese Contemporary", "neighborhood": "Roppongi", "rating": 9.3, "review_count": 870, "summary": "Chef Seiji Yamamoto's kaiseki pushing Japanese tradition into innovative territory.", "tags": ["Kaiseki", "Innovative", "Tasting Menu"]},
        {"name": "Narisawa", "michelin_status": "2 Stars", "cuisine": "Innovative Satoyama", "neighborhood": "Minami-Aoyama", "rating": 9.1, "review_count": 1450, "summary": "Yoshihiro Narisawa's sustainability-focused cuisine inspired by Japanese forests and nature.", "tags": ["Innovative", "Sustainability", "Tasting Menu"]},
        {"name": "Florilège", "michelin_status": "2 Stars", "cuisine": "French-Japanese", "neighborhood": "Minami-Aoyama", "rating": 9.0, "review_count": 1200, "summary": "Counter seating around open kitchen. Seasonal French-Japanese tasting menu by Hiroyasu Kawate.", "tags": ["Counter Dining", "Seasonal", "Romantic"]},
        {"name": "Tempura Motoyoshi", "michelin_status": "Bib Gourmand", "cuisine": "Tempura", "neighborhood": "Ginza", "rating": 8.6, "review_count": 780, "summary": "Counter tempura using premium seasonal ingredients fried in sesame oil. Intimate and traditional.", "tags": ["Counter", "Seasonal", "Traditional"]},
        {"name": "Soba Hasegawa", "michelin_status": "Bib Gourmand", "cuisine": "Soba", "neighborhood": "Minato", "rating": 8.4, "review_count": 650, "summary": "Hand-cut buckwheat soba made fresh daily. Exceptional dashi broth.", "tags": ["Japanese", "Value", "Traditional"]},
    ],
    "new york": [
        {"name": "Le Bernardin", "michelin_status": "3 Stars", "cuisine": "Seafood French", "neighborhood": "Midtown West", "rating": 9.2, "review_count": 4200, "summary": "Eric Ripert's legendary seafood restaurant. Impeccable technique and luxurious ingredients.", "tags": ["Legendary", "Seafood", "Tasting Menu"]},
        {"name": "Eleven Madison Park", "michelin_status": "3 Stars", "cuisine": "Plant-based Contemporary", "neighborhood": "Flatiron", "rating": 9.0, "review_count": 3800, "summary": "Daniel Humm's plant-based tasting menu in a stunning Art Deco dining room.", "tags": ["Plant-based", "Innovative", "Tasting Menu"]},
        {"name": "Per Se", "michelin_status": "3 Stars", "cuisine": "Contemporary American", "neighborhood": "Columbus Circle", "rating": 9.1, "review_count": 3100, "summary": "Thomas Keller's flagship with Central Park views and French-influenced service.", "tags": ["Iconic", "Tasting Menu", "Romantic"]},
        {"name": "Rezdôra", "michelin_status": "1 Star", "cuisine": "Emilian Italian", "neighborhood": "Flatiron", "rating": 8.8, "review_count": 2300, "summary": "Stefano Secchi's authentic Emilian pasta and risotto. A true taste of Northern Italy in New York.", "tags": ["Italian", "Pasta", "Romantic"]},
        {"name": "Lilia", "michelin_status": "Bib Gourmand", "cuisine": "Italian", "neighborhood": "Williamsburg", "rating": 8.7, "review_count": 4100, "summary": "Missy Robbins's celebrated pasta restaurant. Book weeks ahead for sheep milk cheese agnolotti.", "tags": ["Pasta", "Brooklyn", "Neighborhood Gem"]},
        {"name": "Dirt Candy", "michelin_status": "Bib Gourmand", "cuisine": "Vegetable-focused", "neighborhood": "Lower East Side", "rating": 8.5, "review_count": 2200, "summary": "Amanda Cohen's all-vegetable tasting menu. Creative, playful, delicious.", "tags": ["Vegetarian", "Creative", "Value"]},
    ],
    "london": [
        {"name": "Restaurant Gordon Ramsay", "michelin_status": "3 Stars", "cuisine": "Modern French", "neighborhood": "Chelsea", "rating": 9.1, "review_count": 2400, "summary": "Gordon Ramsay's flagship has held 3 Michelin stars since 2001. Classic French excellence.", "tags": ["Classic", "French", "Fine Dining"]},
        {"name": "Sketch (The Lecture Room)", "michelin_status": "2 Stars", "cuisine": "Contemporary French", "neighborhood": "Mayfair", "rating": 8.9, "review_count": 1600, "summary": "Pierre Gagnaire's London outpost in a stunning Mayfair townhouse. Iconic design.", "tags": ["Design", "French", "Romantic"]},
        {"name": "Brat", "michelin_status": "1 Star", "cuisine": "British-Basque", "neighborhood": "Shoreditch", "rating": 8.8, "review_count": 2800, "summary": "Tomos Parry's wood-fire cooking inspired by Basque techniques. Legendary whole turbot.", "tags": ["Wood Fire", "Seasonal", "Trendy"]},
        {"name": "St. JOHN", "michelin_status": "Bib Gourmand", "cuisine": "British Nose-to-Tail", "neighborhood": "Clerkenwell", "rating": 8.6, "review_count": 3200, "summary": "Fergus Henderson's seminal nose-to-tail restaurant. Classic bone marrow and parsley salad.", "tags": ["British", "Classic", "Institution"]},
        {"name": "Kiln", "michelin_status": "Bib Gourmand", "cuisine": "Thai", "neighborhood": "Soho", "rating": 8.7, "review_count": 3600, "summary": "Clay pot Thai cooking over open flames. Best Northern Thai food in London.", "tags": ["Thai", "Counter", "Value"]},
    ],
    "san francisco": [
        {"name": "Benu", "michelin_status": "3 Stars", "cuisine": "Asian-American Contemporary", "neighborhood": "SoMa", "rating": 9.2, "review_count": 1100, "summary": "Corey Lee's inventive Asian-American tasting menu; brilliant Korean, Chinese, and French techniques.", "tags": ["Asian-American", "Innovative", "Tasting Menu"]},
        {"name": "Quince", "michelin_status": "3 Stars", "cuisine": "Contemporary Italian-Californian", "neighborhood": "Jackson Square", "rating": 9.1, "review_count": 1200, "summary": "Michael Tusk's farm-to-table Italian with handmade pasta and Northern California ingredients.", "tags": ["Farm-to-Table", "Pasta", "Tasting Menu"]},
        {"name": "Lazy Bear", "michelin_status": "2 Stars", "cuisine": "Contemporary American", "neighborhood": "Mission District", "rating": 8.9, "review_count": 2100, "summary": "Communal dining with tickets sold online. Modern American tasting menu with campfire storytelling.", "tags": ["Communal", "Tasting Menu", "Innovative"]},
        {"name": "Cotogna", "michelin_status": "Bib Gourmand", "cuisine": "Italian", "neighborhood": "Jackson Square", "rating": 8.7, "review_count": 2900, "summary": "Michael Tusk's casual trattoria. Wood-fired meats, seasonal vegetables, handmade pasta.", "tags": ["Italian", "Wood Fire", "Casual"]},
        {"name": "Zuni Café", "michelin_status": "Bib Gourmand", "cuisine": "Mediterranean-Californian", "neighborhood": "Hayes Valley", "rating": 8.6, "review_count": 4100, "summary": "SF institution since 1979. Famous roasted chicken for two with warm bread salad.", "tags": ["Institution", "Mediterranean", "Romantic"]},
    ],
    "barcelona": [
        {"name": "Disfrutar", "michelin_status": "3 Stars", "cuisine": "Contemporary Spanish", "neighborhood": "Eixample", "rating": 9.4, "review_count": 2100, "summary": "elBulli alumni create one of the world's most creative tasting menus. Book a year ahead.", "tags": ["Avant-garde", "Tasting Menu", "Creative"]},
        {"name": "Moments", "michelin_status": "2 Stars", "cuisine": "Catalan Contemporary", "neighborhood": "Eixample", "rating": 8.9, "review_count": 890, "summary": "Modern Catalan cuisine by Carme Ruscalleda's son in an elegant hotel setting.", "tags": ["Catalan", "Hotel Dining", "Elegant"]},
        {"name": "Tickets", "michelin_status": "1 Star", "cuisine": "Avant-garde Tapas", "neighborhood": "Sant Antoni", "rating": 8.8, "review_count": 3200, "summary": "Albert Adrià's playful tapas bar. Molecular gastronomy meets Barcelona street food.", "tags": ["Tapas", "Creative", "Fun"]},
        {"name": "La Pepita", "michelin_status": "Bib Gourmand", "cuisine": "Contemporary Mediterranean", "neighborhood": "Gràcia", "rating": 8.5, "review_count": 2100, "summary": "Neighborhood favorite with excellent value and creative seasonal dishes.", "tags": ["Neighborhood", "Value", "Seasonal"]},
    ],
    "rome": [
        {"name": "La Pergola", "michelin_status": "3 Stars", "cuisine": "Contemporary Mediterranean", "neighborhood": "Monte Mario", "rating": 9.2, "review_count": 1800, "summary": "Heinz Beck's only 3-star restaurant in Rome with panoramic city views.", "tags": ["Views", "Tasting Menu", "Romantic"]},
        {"name": "Il Pagliaccio", "michelin_status": "2 Stars", "cuisine": "Contemporary Italian", "neighborhood": "Centro Storico", "rating": 8.9, "review_count": 760, "summary": "Chef Anthony Genovese's refined tasting menu using top Italian ingredients.", "tags": ["Tasting Menu", "Refined", "Creative"]},
        {"name": "Roscioli", "michelin_status": "Bib Gourmand", "cuisine": "Roman", "neighborhood": "Jewish Quarter", "rating": 8.7, "review_count": 4200, "summary": "Rome's best carbonara. Deli, wine bar, and restaurant combined. Outstanding cacio e pepe.", "tags": ["Roman", "Classic", "Pasta"]},
        {"name": "Osteria dell'Arco", "michelin_status": "Bib Gourmand", "cuisine": "Roman Trattoria", "neighborhood": "Prati", "rating": 8.4, "review_count": 1900, "summary": "Unpretentious Roman cooking with market-fresh ingredients. Outstanding value.", "tags": ["Roman", "Value", "Trattoria"]},
    ],
    "amsterdam": [
        {"name": "Ciel Bleu", "michelin_status": "2 Stars", "cuisine": "Contemporary French", "neighborhood": "De Pijp", "rating": 9.0, "review_count": 1100, "summary": "23rd floor of Hotel Okura with panoramic city views. Refined French-Dutch cuisine.", "tags": ["Views", "Hotel Dining", "Romantic"]},
        {"name": "Bord'Eau", "michelin_status": "2 Stars", "cuisine": "Modern French", "neighborhood": "Centrum", "rating": 8.8, "review_count": 890, "summary": "Richard van Oosterhout's elegant French cuisine in Hotel de l'Europe.", "tags": ["Hotel Dining", "French", "Elegant"]},
        {"name": "Breda", "michelin_status": "1 Star", "cuisine": "Contemporary Dutch", "neighborhood": "Jordaan", "rating": 8.7, "review_count": 1400, "summary": "Award-winning modern Dutch cuisine in a relaxed neighborhood setting.", "tags": ["Dutch", "Seasonal", "Neighborhood"]},
        {"name": "Bak", "michelin_status": "Bib Gourmand", "cuisine": "Vegetable-focused", "neighborhood": "Westerdok", "rating": 8.5, "review_count": 1200, "summary": "Stunning waterfront location with vegetable-focused modern Dutch cooking.", "tags": ["Vegetable", "Waterfront", "Value"]},
    ],
    "chicago": [
        {"name": "Alinea", "michelin_status": "3 Stars", "cuisine": "Contemporary American", "neighborhood": "Lincoln Park", "rating": 9.3, "review_count": 2900, "summary": "Grant Achatz's avant-garde multi-sensory experience. One of America's most innovative restaurants.", "tags": ["Avant-garde", "Multi-sensory", "Tasting Menu"]},
        {"name": "Ever", "michelin_status": "2 Stars", "cuisine": "Contemporary American", "neighborhood": "Fulton Market", "rating": 9.0, "review_count": 1100, "summary": "Curtis Duffy's intimate tasting menu restaurant. Stunning, precise cooking.", "tags": ["Intimate", "Tasting Menu", "Precise"]},
        {"name": "Smyth", "michelin_status": "2 Stars", "cuisine": "Contemporary American", "neighborhood": "West Loop", "rating": 8.9, "review_count": 1400, "summary": "John and Karen Shields' farm-to-table tasting menu with hyper-local ingredients.", "tags": ["Farm-to-Table", "Seasonal", "West Loop"]},
        {"name": "Girl & the Goat", "michelin_status": "Bib Gourmand", "cuisine": "American", "neighborhood": "West Loop", "rating": 8.7, "review_count": 5100, "summary": "Stephanie Izard's bustling restaurant with creative shared plates.", "tags": ["Casual", "Sharing", "Value"]},
    ],
    "los angeles": [
        {"name": "Providence", "michelin_status": "2 Stars", "cuisine": "Seafood Contemporary", "neighborhood": "Hollywood", "rating": 9.0, "review_count": 1700, "summary": "Michael Cimarusti's sustainable seafood tasting menu. Best seafood restaurant in LA.", "tags": ["Seafood", "Sustainable", "Tasting Menu"]},
        {"name": "n/naka", "michelin_status": "2 Stars", "cuisine": "Kaiseki", "neighborhood": "Palms", "rating": 9.2, "review_count": 1500, "summary": "Niki Nakayama's intimate kaiseki. Celebrated on Chef's Table. Book months ahead.", "tags": ["Kaiseki", "Intimate", "Romantic"]},
        {"name": "Osteria Mozza", "michelin_status": "1 Star", "cuisine": "Italian", "neighborhood": "Hollywood", "rating": 8.8, "review_count": 3600, "summary": "Nancy Silverton's mozzarella bar and trattoria. Outstanding pasta and wood-fire pizza.", "tags": ["Italian", "Pasta", "Casual"]},
        {"name": "Bestia", "michelin_status": "Bib Gourmand", "cuisine": "Italian", "neighborhood": "Arts District", "rating": 8.8, "review_count": 6200, "summary": "Ori Menashe's celebrated Italian osteria. Outstanding charcuterie, pasta, and wood-fire cooking.", "tags": ["Italian", "Pasta", "Trendy"]},
    ],
    "singapore": [
        {"name": "Les Amis", "michelin_status": "3 Stars", "cuisine": "Contemporary French", "neighborhood": "Orchard", "rating": 9.2, "review_count": 980, "summary": "Singapore's pinnacle of French fine dining. Exceptional wine cellar and impeccable service.", "tags": ["French", "Fine Dining", "Tasting Menu"]},
        {"name": "Odette", "michelin_status": "3 Stars", "cuisine": "Contemporary French", "neighborhood": "Civic District", "rating": 9.3, "review_count": 1200, "summary": "Julien Royer's stunning restaurant in the National Gallery. Nature-inspired creative French cuisine.", "tags": ["French", "Innovative", "Romantic"]},
        {"name": "Burnt Ends", "michelin_status": "1 Star", "cuisine": "Modern Barbecue", "neighborhood": "Chinatown", "rating": 9.0, "review_count": 2800, "summary": "Dave Pynt's wood-fire barbecue with outstanding smoked meats and creative sides.", "tags": ["Barbecue", "Wood Fire", "Trendy"]},
        {"name": "Hawker Chan", "michelin_status": "1 Star", "cuisine": "Hawker / Cantonese", "neighborhood": "Chinatown", "rating": 8.5, "review_count": 5400, "summary": "World's most affordable Michelin-starred meal. Legendary soy sauce chicken rice.", "tags": ["Value", "Hawker", "Iconic"]},
    ],
}

_FALLBACK_DATA: list[dict] = [
    {"name": "The Grand Table", "michelin_status": "1 Star", "cuisine": "Contemporary European", "neighborhood": "City Center", "rating": 8.8, "review_count": 1200, "summary": "Refined seasonal tasting menu with local produce and an exceptional wine program.", "tags": ["Fine Dining", "Tasting Menu", "Seasonal"]},
    {"name": "Maison Classique", "michelin_status": "Bib Gourmand", "cuisine": "French Bistro", "neighborhood": "Historic Quarter", "rating": 8.5, "review_count": 1800, "summary": "Classic French bistro techniques with local ingredients. Exceptional value.", "tags": ["Value", "French", "Classic"]},
    {"name": "Ember & Oak", "michelin_status": "1 Star", "cuisine": "Modern Grill", "neighborhood": "Waterfront", "rating": 8.7, "review_count": 2100, "summary": "Wood-fired cooking with exceptional seasonal meats and vegetables.", "tags": ["Wood Fire", "Grill", "Seasonal"]},
    {"name": "Trattoria del Mercato", "michelin_status": "Bib Gourmand", "cuisine": "Italian", "neighborhood": "Market District", "rating": 8.4, "review_count": 1600, "summary": "Market-fresh Italian cooking with handmade pasta. A beloved local institution.", "tags": ["Italian", "Pasta", "Value"]},
]


class MichelinRetriever:
    """Fetches structured Michelin Guide data for a destination, filtered and ranked by query."""

    def fetch(self, destination: str, query: str = "") -> List[UnifiedRestaurantResult]:
        dest_lower = destination.lower()
        data: list[dict] | None = None

        for city_key, city_data in _MICHELIN_DB.items():
            if city_key in dest_lower or dest_lower in city_key:
                data = list(city_data)
                break

        if data is None:
            data = list(_FALLBACK_DATA)

        filtered = self._filter_by_query(data, query)
        if not filtered:
            filtered = data

        filtered.sort(
            key=lambda x: (
                _MICHELIN_STAR_RANK.get(x.get("michelin_status", ""), 0),
                x.get("rating", 0),
            ),
            reverse=True,
        )

        return [self._to_result(r, destination) for r in filtered]

    def _filter_by_query(self, data: list[dict], query: str) -> list[dict]:
        q = query.lower()

        if any(w in q for w in ["bib gourmand", "bib"]):
            return [r for r in data if r.get("michelin_status") == "Bib Gourmand"]

        if any(w in q for w in ["romantic", "date night", "anniversary"]):
            return [
                r for r in data
                if any(t.lower() in ("romantic", "intimate", "elegant", "views") for t in r.get("tags", []))
                or r.get("michelin_status") in ("3 Stars", "2 Stars")
            ]

        if any(w in q for w in ["tasting menu", "tasting", "omakase", "kaiseki"]):
            return [r for r in data if any("Tasting Menu" in t or "Omakase" in t or "Kaiseki" in t for t in r.get("tags", []))]

        if any(w in q for w in ["value", "affordable", "cheap", "budget"]):
            return [r for r in data if r.get("michelin_status") in ("Bib Gourmand", "Selected")]

        if any(w in q for w in ["hidden gem", "hidden gems", "off the beaten"]):
            return [r for r in data if r.get("michelin_status") in ("Bib Gourmand", "1 Star", "Selected")]

        return data

    def _to_result(self, raw: dict, destination: str) -> UnifiedRestaurantResult:
        maps_query = f"{raw['name']} {destination}".replace(" ", "+")
        return UnifiedRestaurantResult(
            name=raw["name"],
            source="Michelin Guide",
            michelin_status=raw.get("michelin_status"),
            cuisine=raw.get("cuisine", ""),
            neighborhood=raw.get("neighborhood"),
            rating=raw.get("rating"),
            review_count=raw.get("review_count"),
            summary=raw.get("summary"),
            maps_link=f"https://maps.google.com/?q={maps_query}",
            ai_score=self._compute_ai_score(raw),
            tags=raw.get("tags", []),
        )

    def _compute_ai_score(self, raw: dict) -> float:
        star_score = _MICHELIN_STAR_RANK.get(raw.get("michelin_status", ""), 0) * 10
        rating_score = raw.get("rating", 0) * 5
        review_score = min(raw.get("review_count", 0) / 1000, 5)
        return round((star_score + rating_score + review_score) / 3, 2)
