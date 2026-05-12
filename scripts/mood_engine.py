"""
mood_engine.py — Mood detection e generazione keyword/prompt per le immagini.
"""

# ── Dizionario emozionale IT→EN ───────────────────────────────────────────────
MOOD_DICT = {
    'volare':    ['open sky', 'clouds sunrise', 'freedom blue sky', 'soaring clouds'],
    'cielo':     ['starry sky', 'moonlight clouds', 'blue sky dreamy'],
    'mare':      ['sea sunset', 'ocean waves horizon', 'beach golden hour'],
    'amore':     ['romantic sunset', 'warm golden light', 'soft dreamy horizon'],
    'cuore':     ['warm sunset glow', 'romantic landscape', 'emotional light'],
    'ricordi':   ['nostalgic road evening', 'old street sunset', 'memory landscape'],
    'notte':     ['night city lights', 'moonlight stars', 'dark blue sky urban'],
    'estate':    ['beach golden hour', 'blue sea summer', 'warm sand sunset'],
    'sogno':     ['dreamy sky aurora', 'soft clouds surreal', 'fantasy landscape'],
    'noi':       ['romantic sunset city', 'warm evening horizon', 'two silhouettes'],
    'sole':      ['golden sunrise bright', 'sunshine warm', 'summer light sky'],
    'luna':      ['moonlight night', 'moon reflection stars', 'midnight sky'],
    'pioggia':   ['rain window night', 'wet road moody', 'blue hour rain'],
    'lacrime':   ['lonely road night', 'blue hour misty', 'melancholic rain'],
    'libertà':   ['open sky birds', 'wide horizon wind', 'open road freedom'],
    'strada':    ['open road highway sunset', 'journey adventure'],
    'città':     ['city lights night', 'urban skyline bokeh', 'metropolitan evening'],
    'montagna':  ['mountain sunrise mist', 'alpine landscape peaks', 'nature fog'],
    'inverno':   ['snow landscape winter', 'frost cold blue', 'white silence'],
    'primavera': ['spring flowers green', 'cherry blossom soft light', 'renewal'],
    'autunno':   ['autumn leaves golden', 'fall forest warm', 'misty morning'],
    'vita':      ['open road sunrise', 'new beginning hope', 'life journey'],
    'speranza':  ['sunrise horizon dawn', 'morning light bright', 'new day hope'],
    'silenzio':  ['misty lake quiet', 'fog peaceful landscape', 'still water calm'],
    'musica':    ['concert atmosphere', 'stage lights bokeh', 'music vibes light'],
    'ballo':     ['dance light stage', 'neon lights club', 'spotlight dance'],
    'sempre':    ['starry night eternal', 'timeless landscape infinite', 'starry sky'],
    'lontano':   ['distant horizon far', 'long road sunset', 'sunset over sea'],
    'felicità':  ['golden hour bright', 'joyful sunshine', 'happy light nature'],
    'tristezza': ['rainy window night', 'lonely road fog', 'blue hour melancholy'],
    'alba':      ['dawn sunrise horizon', 'morning golden light', 'new day sky'],
    'tramonto':  ['golden sunset sky', 'warm evening horizon', 'dusk colors'],
    'oceano':    ['ocean waves horizon', 'deep sea sunset', 'vast ocean sky'],
    'bosco':     ['forest light trees', 'woodland mist morning', 'green nature'],
    'vento':     ['wind clouds movement', 'open field sky', 'breezy landscape'],
}

TAG_MOOD = {
    'amore': 'romantic', 'romantico': 'romantic',
    'estate': 'summer',  'mare': 'sea',
    'nostalgia': 'melancholic', 'malinconia': 'melancholic',
    'notte': 'nocturnal', 'stelle': 'nocturnal',
    'libertà': 'freedom', 'volare': 'freedom',
    'sogno': 'dreamy',   'energia': 'energetic',
    'speranza': 'hopeful', 'alba': 'hopeful',
    'inverno': 'winter', 'autunno': 'autumn',
    'primavera': 'spring', 'sole': 'summer',
}

MOOD_PALETTE = {
    'romantic':   {'c1': (60, 10, 80),   'c2': (140, 30, 100), 'c3': (200, 80, 140)},
    'melancholic':{'c1': (8, 15, 50),    'c2': (25, 40, 90),   'c3': (60, 80, 130)},
    'summer':     {'c1': (180, 80, 10),  'c2': (230, 140, 30), 'c3': (20, 80, 180)},
    'nocturnal':  {'c1': (4, 4, 25),     'c2': (15, 8, 50),    'c3': (60, 20, 100)},
    'freedom':    {'c1': (15, 60, 160),  'c2': (60, 120, 210), 'c3': (180, 210, 255)},
    'sea':        {'c1': (8, 30, 90),    'c2': (15, 70, 140),  'c3': (190, 130, 50)},
    'dreamy':     {'c1': (70, 30, 110),  'c2': (130, 60, 160), 'c3': (200, 150, 220)},
    'energetic':  {'c1': (180, 15, 70),  'c2': (220, 70, 15),  'c3': (90, 15, 180)},
    'hopeful':    {'c1': (15, 50, 110),  'c2': (70, 110, 190), 'c3': (210, 185, 110)},
    'winter':     {'c1': (20, 30, 70),   'c2': (60, 90, 150),  'c3': (200, 210, 230)},
    'autumn':     {'c1': (100, 40, 10),  'c2': (180, 90, 20),  'c3': (220, 160, 60)},
    'spring':     {'c1': (30, 100, 60),  'c2': (80, 170, 100), 'c3': (220, 200, 180)},
    'default':    {'c1': (8, 6, 25),     'c2': (35, 15, 70),   'c3': (80, 25, 120)},
}

FALLBACK_QUERIES = [
    'cinematic emotional landscape sunset sky',
    'starry sky cinematic night',
    'sea sunset horizon dreamy',
    'romantic city lights night',
    'mountain sunrise golden hour',
    'aurora borealis night sky',
    'dreamy clouds morning light',
]


def _normalize(text: str) -> str:
    return text.lower().replace("'", " ").replace(",", " ")


def detect_mood(song_title: str, dedication_text: str,
                short_phrase: str, tags: str) -> str:
    text = _normalize(f"{song_title} {dedication_text} {short_phrase} {tags}")
    for tag in _normalize(tags).split():
        if tag in TAG_MOOD:
            return TAG_MOOD[tag]
    checks = [
        ('romantic',    ['amore', 'cuore', 'baci', 'romantico', 'noi', 'insieme']),
        ('sea',         ['mare', 'spiaggia', 'onde', 'oceano']),
        ('nocturnal',   ['notte', 'stelle', 'luna', 'buio', 'mezzanotte']),
        ('summer',      ['estate', 'sole', 'caldo', 'vacanza']),
        ('freedom',     ['libertà', 'volare', 'cielo', 'vento', 'ali']),
        ('dreamy',      ['sogno', 'fantasia', 'magia', 'incanto']),
        ('melancholic', ['tristezza', 'lacrime', 'pianto', 'malinconia', 'dolore', 'pioggia']),
        ('hopeful',     ['speranza', 'domani', 'futuro', 'luce', 'alba']),
    ]
    for mood, words in checks:
        if any(w in text for w in words):
            return mood
    return 'default'


def generate_visual_keywords(song_title: str, dedication_text: str,
                              short_phrase: str, tags: str) -> list:
    text = _normalize(f"{song_title} {dedication_text} {short_phrase} {tags}")
    keywords = []
    for it_word, en_kws in MOOD_DICT.items():
        if it_word in text:
            keywords.extend(en_kws[:2])
    seen, unique = set(), []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    if len(unique) < 2:
        mood = detect_mood(song_title, dedication_text, short_phrase, tags)
        unique.insert(0, FALLBACK_QUERIES[0])
    return unique[:6]


def generate_search_query(song_title: str, dedication_text: str,
                           short_phrase: str, tags: str) -> str:
    kws = generate_visual_keywords(song_title, dedication_text, short_phrase, tags)
    return ' '.join(kws[:3]) if kws else FALLBACK_QUERIES[0]


def generate_gemini_prompt(song_title: str, artist: str, dedication_text: str,
                            short_phrase: str, tags: str) -> str:
    excerpt = dedication_text[:200] + ('...' if len(dedication_text) > 200 else '')
    return (
        f'Create a cinematic emotional premium background image inspired by an Italian music dedication.\n'
        f'Song title: "{song_title}"\nArtist: "{artist}"\n'
        f'Dedication text: "{excerpt}"\nShort phrase: "{short_phrase}"\nTags: "{tags}"\n\n'
        'The image must evoke the emotional atmosphere of the dedication and the song.\n'
        'Prefer beautiful evocative landscapes: sea, sunsets, sunrise, starry sky, moonlight, '
        'aurora, clouds, mountains, open roads, romantic city lights, dreamy horizons.\n\n'
        'Style: cinematic photography, premium music cover aesthetic, emotional and poetic mood, '
        'dark elegant color grading, soft neon or golden light, atmospheric lighting, '
        'vertical composition, suitable as a hero image for a music dedication website.\n\n'
        'Important: no text, no logos, no watermarks, no album covers, no celebrities, '
        'no recognizable close-up faces, no copyrighted artwork.'
    )
