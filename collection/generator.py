import random, json, os, hashlib
from PIL import Image

random.seed(5000)
OUT = '/workspace/npcshood'
os.makedirs(f'{OUT}/images', exist_ok=True)
os.makedirs(f'{OUT}/metadata', exist_ok=True)
N = 32
SCALE = 16
K = (12, 10, 20)  # outline colour (near-black)

def pick(d):
    names = list(d.keys()); w = [d[n][0] for n in names]
    return random.choices(names, w)[0]

BG = {  # name: (weight, base, detail)
 'Town Grass': (20, (126, 186, 132), (100, 160, 108)),
 'Dungeon Stone': (16, (92, 92, 110), (72, 72, 90)),
 'Desert Sand': (14, (232, 200, 130), (210, 176, 106)),
 'Night Sky': (16, (44, 40, 104), (240, 240, 255)),
 'Snowfield': (12, (210, 228, 240), (255, 255, 255)),
 'Ocean': (12, (70, 140, 210), (120, 190, 240)),
 'Lava': (5, (150, 36, 30), (255, 140, 40)),
 'Glitch': (3, (20, 20, 30), (255, 0, 200)),
 'Gold Vault': (2, (230, 180, 50), (255, 230, 120)),
}
SKIN = {
 'Light': (22, (246, 206, 170), (220, 170, 136)),
 'Tan': (22, (224, 170, 120), (196, 140, 96)),
 'Brown': (18, (170, 110, 70), (140, 86, 52)),
 'Dark': (14, (110, 70, 46), (84, 52, 34)),
 'Zombie': (7, (140, 190, 120), (104, 150, 90)),
 'Robot': (6, (170, 180, 196), (120, 130, 150)),
 'Ghost': (5, (236, 240, 255), (196, 204, 230)),
 'Alien': (4, (120, 200, 230), (80, 160, 200)),
 'Gold': (2, (250, 210, 60), (210, 160, 30)),
}
HOODIE = {
 'Mustard': (12, (212, 160, 50), (170, 120, 30)),
 'Teal': (12, (80, 150, 150), (50, 110, 115)),
 'Red': (11, (200, 60, 60), (150, 36, 40)),
 'Black': (11, (50, 48, 60), (30, 28, 40)),
 'Purple': (10, (120, 80, 170), (86, 54, 130)),
 'Forest': (10, (70, 130, 70), (46, 96, 50)),
 'Pink': (9, (240, 140, 180), (200, 100, 140)),
 'Sky': (9, (110, 170, 240), (70, 130, 200)),
 'White': (8, (236, 236, 240), (190, 190, 205)),
 'Camo': (5, (110, 120, 70), (80, 90, 50)),
 'Rainbow': (2, None, None),
 'Diamond': (1, (170, 240, 255), (110, 200, 230)),
}
HEAD = {  # headwear; Hood Up means hood covers head
 'Hood Up': (40,), 'Guard Helmet': (9,), 'Wizard Hat': (8,), 'Cap': (10,), 'Straw Hat': (8,),
 'Bandana': (8,), 'Chef Hat': (5,), 'Horns': (5,), 'Halo': (3,), 'Crown': (2,),
}
EYES = {'Blank Dots': (30,), 'Sleepy': (16,), 'Angry': (12,), 'Wide': (12,), 'Wink': (8,),
        'Shades': (9,), 'Glowing': (5,), 'Laser': (3,), 'X Eyes': (5,)}
MOUTH = {'Flat': (34,), 'Smile': (18,), 'Frown': (12,), 'Open': (12,), 'Smirk': (12,), 'Mask': (7,), 'Beard': (5,)}
ITEM = {'None': (22,), 'Coffee Cup': (12,), 'Sword': (11,), 'Wooden Staff': (9,), 'Potion': (10,), 'Torch': (8,),
        'Fish': (8,), 'Coin Bag': (8,), 'Shield': (7,), 'Broom': (5,)}
OVER = {'None': (28,), 'Quest !': (18,), 'Quest ?': (12,), 'HP Bar': (14,), 'Zzz': (10,), 'Heart': (8,),
        'Speech ...': (8,), 'Level Up': (2,)}

RAINBOW = [(230, 60, 60), (240, 150, 40), (240, 220, 60), (80, 190, 90), (70, 140, 230), (140, 80, 200)]

def make(t):
    g = [[None] * N for _ in range(N)]
    bgname = t['Background']; bg, det = BG[bgname][1], BG[bgname][2]
    sk, skd = SKIN[t['Skin']][1], SKIN[t['Skin']][2]
    hn = t['Hoodie']
    def hc(x, y, shade=False):
        if hn == 'Rainbow':
            c = RAINBOW[(y // 2) % 6]
            return tuple(max(0, v - 40) for v in c) if shade else c
        return HOODIE[hn][2] if shade else HOODIE[hn][1]
    def put(x, y, c):
        if 0 <= x < N and 0 <= y < N: g[y][x] = c
    def rect(x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                put(x, y, c(x, y) if callable(c) else c)

    # body / hoodie (rounded shoulders)
    for y in range(23, 32):
        inset = max(0, 3 - (y - 23))
        rect(6 + inset, y, 25 - inset, y, lambda x, y: hc(x, y))
    # shading + center seam + pocket + strings
    for y in range(24, 32): put(6 + max(0, 3 - (y - 23)), y, hc(0, y, True))
    rect(11, 28, 20, 28, lambda x, y: hc(x, y, True))
    put(13, 23, (230, 230, 230)); put(13, 24, (230, 230, 230)); put(18, 23, (230, 230, 230)); put(18, 24, (230, 230, 230))
    # neck
    rect(14, 21, 17, 22, skd)

    hood_up = t['Head'] == 'Hood Up'
    if hood_up:
        # hood frame around face
        for y in range(8, 24):
            w = 7 if y > 10 else (5 if y == 9 else 6) if y > 8 else 4
            rect(15 - w, y, 16 + w, y, lambda x, y: hc(x, y))
        rect(9, 10, 9, 22, lambda x, y: hc(x, y, True))
    else:
        # hood down: bunched collar
        rect(9, 21, 22, 23, lambda x, y: hc(x, y, True))
    # face
    rect(11, 11, 20, 20, sk)
    rect(11, 20, 20, 20, skd)
    rect(12, 21, 19, 21, skd)
    if not hood_up:
        # ears
        put(10, 15, sk); put(10, 16, skd); put(21, 15, sk); put(21, 16, skd)
        # hair line
        hair = random.Random(t['seed']).choice([(60, 40, 30), (30, 25, 25), (180, 120, 60), (220, 200, 120), (150, 50, 40)])
        if t['Skin'] in ('Robot', 'Ghost', 'Alien', 'Gold'): hair = skd
        rect(11, 10, 20, 11, hair); put(11, 12, hair); put(20, 12, hair)
    if t['Skin'] == 'Robot':
        put(15, 9, (120, 130, 150)); put(16, 9, (120, 130, 150)); put(15, 8, (255, 80, 80))
    # cheeks blush
    if t['Skin'] not in ('Robot', 'Ghost', 'Zombie', 'Gold'):
        put(12, 18, (240, 140, 140)); put(19, 18, (240, 140, 140))

    # eyes (row 15-16), positions x 13 and 18
    e = t['Eyes']; W = (255, 255, 255)
    if e == 'Blank Dots':
        put(13, 15, K); put(13, 16, K); put(18, 15, K); put(18, 16, K)
    elif e == 'Sleepy':
        rect(12, 15, 14, 15, K); rect(17, 15, 19, 15, K); put(13, 16, K); put(18, 16, K)
    elif e == 'Angry':
        put(12, 14, K); put(13, 15, K); put(19, 14, K); put(18, 15, K); put(13, 16, K); put(18, 16, K)
    elif e == 'Wide':
        rect(12, 14, 14, 16, W); put(13, 15, K); rect(17, 14, 19, 16, W); put(18, 15, K)
    elif e == 'Wink':
        put(13, 15, K); put(13, 16, K); rect(17, 16, 19, 16, K)
    elif e == 'Shades':
        rect(11, 14, 20, 14, K); rect(12, 15, 14, 16, K); rect(17, 15, 19, 16, K); put(12, 15, (90, 90, 120)); put(17, 15, (90, 90, 120))
    elif e == 'Glowing':
        rect(12, 15, 14, 16, (120, 255, 230)); rect(17, 15, 19, 16, (120, 255, 230))
    elif e == 'Laser':
        put(13, 15, (255, 40, 40)); put(18, 15, (255, 40, 40))
        for x in range(19, 32): put(x, 15, (255, 60, 60)); put(x, 16, (255, 160, 160)) if x % 2 else None
        for x in range(0, 13): put(x, 15, (255, 60, 60))
    elif e == 'X Eyes':
        for (cx) in (13, 18):
            put(cx - 1, 14, K); put(cx + 1, 14, K); put(cx, 15, K); put(cx - 1, 16, K); put(cx + 1, 16, K)

    m = t['Mouth']
    if m == 'Flat': rect(14, 18, 17, 18, K)
    elif m == 'Smile': put(13, 17, K); rect(14, 18, 17, 18, K); put(18, 17, K)
    elif m == 'Frown': put(13, 19, K); rect(14, 18, 17, 18, K); put(18, 19, K)
    elif m == 'Open': rect(14, 18, 17, 19, K); rect(15, 19, 16, 19, (220, 80, 90))
    elif m == 'Smirk': rect(14, 18, 16, 18, K); put(17, 17, K)
    elif m == 'Mask': rect(11, 17, 20, 20, (90, 90, 100)); rect(11, 17, 20, 17, (60, 60, 70))
    elif m == 'Beard': rect(11, 18, 20, 21, (110, 70, 40)); rect(14, 18, 17, 18, K); rect(12, 22, 19, 22, (110, 70, 40))

    h = t['Head']
    if h == 'Guard Helmet':
        rect(10, 8, 21, 12, (160, 165, 180)); rect(10, 12, 21, 12, (110, 115, 130)); rect(15, 5, 16, 8, (200, 50, 50)); rect(10, 13, 10, 17, (110, 115, 130)); rect(21, 13, 21, 17, (110, 115, 130))
    elif h == 'Wizard Hat':
        hatc = (60, 60, 160)
        for i, y in enumerate(range(2, 11)):
            w = i // 2 + 1
            rect(15 - w + 1, y, 16 + w - 1, y, hatc)
        rect(8, 11, 23, 11, hatc); put(15, 5, (255, 230, 80)); put(17, 8, (255, 230, 80))
    elif h == 'Cap':
        rect(11, 8, 20, 11, (210, 60, 60)); rect(18, 11, 24, 11, (170, 40, 40)); put(15, 8, (255, 255, 255))
    elif h == 'Straw Hat':
        rect(12, 7, 19, 10, (230, 200, 110)); rect(7, 10, 24, 11, (220, 186, 96)); rect(12, 9, 19, 9, (180, 60, 50))
    elif h == 'Bandana':
        rect(11, 10, 20, 12, (200, 50, 60)); put(21, 12, (200, 50, 60)); put(22, 13, (200, 50, 60)); put(14, 11, W); put(18, 11, W)
    elif h == 'Chef Hat':
        rect(11, 4, 20, 10, (250, 250, 250)); rect(10, 5, 21, 7, (250, 250, 250)); rect(11, 10, 20, 10, (210, 210, 220))
    elif h == 'Horns':
        for (x0, d) in ((10, -1), (21, 1)):
            put(x0, 10, (240, 230, 210)); put(x0 + d, 9, (240, 230, 210)); put(x0 + d, 8, (240, 230, 210)); put(x0 + 2 * d, 7, (240, 230, 210))
    elif h == 'Halo':
        rect(12, 5, 19, 5, (255, 230, 90)); put(11, 6, (255, 230, 90)); put(20, 6, (255, 230, 90)); rect(12, 7, 19, 7, (255, 230, 90))
    elif h == 'Crown':
        rect(11, 7, 20, 10, (250, 200, 40)); put(11, 6, (250, 200, 40)); put(15, 5, (250, 200, 40)); put(16, 5, (250, 200, 40)); put(20, 6, (250, 200, 40)); put(15, 8, (220, 40, 60)); put(12, 9, (60, 140, 230)); put(19, 9, (60, 140, 230))

    # hand + item (left side of image, character's right)
    it = t['Item']
    if it != 'None':
        rect(7, 26, 9, 28, sk)
        if it == 'Coffee Cup':
            rect(7, 22, 9, 25, (250, 250, 250)); rect(7, 22, 9, 22, (120, 80, 50)); rect(7, 24, 9, 24, (140, 90, 60))
        elif it == 'Sword':
            rect(8, 10, 8, 24, (210, 215, 230)); put(7, 11, (160, 165, 180)); rect(6, 25, 10, 25, (150, 110, 40)); put(8, 9, (240, 240, 250))
        elif it == 'Wooden Staff':
            rect(8, 8, 8, 31, (130, 90, 50)); rect(7, 6, 9, 8, (90, 220, 255)); put(8, 5, (200, 250, 255))
        elif it == 'Potion':
            rect(7, 21, 9, 25, (220, 60, 120)); rect(8, 19, 8, 20, (200, 200, 220)); put(7, 22, (255, 160, 200))
        elif it == 'Torch':
            rect(8, 18, 8, 25, (120, 80, 40)); rect(7, 15, 9, 17, (255, 160, 40)); put(8, 14, (255, 230, 80)); put(8, 16, (255, 240, 150))
        elif it == 'Fish':
            rect(5, 21, 10, 24, (120, 170, 210)); put(4, 20, (90, 140, 180)); put(4, 25, (90, 140, 180)); put(9, 22, K)
        elif it == 'Coin Bag':
            rect(6, 21, 10, 25, (180, 140, 80)); rect(7, 20, 9, 20, (140, 100, 50)); put(8, 23, (255, 220, 60))
        elif it == 'Shield':
            rect(4, 19, 10, 26, (90, 110, 170)); rect(7, 19, 7, 26, (230, 200, 60)); rect(4, 22, 10, 22, (230, 200, 60))
        elif it == 'Broom':
            rect(8, 8, 8, 25, (150, 110, 60)); rect(6, 4, 10, 8, (220, 190, 100))

    # overhead (top center)
    o = t['Overhead']; Y = (255, 220, 60)
    top = 0 if h in ('Wizard Hat', 'Chef Hat', 'Halo', 'Crown') else 2
    if o != 'None' and h in ('Wizard Hat', 'Chef Hat'):
        cx = 25  # move to the side
    else:
        cx = 15
    if o == 'Quest !':
        rect(cx, top, cx + 1, top + 3, Y); rect(cx, top + 5, cx + 1, top + 5, Y)
    elif o == 'Quest ?':
        rect(cx - 1, top, cx + 2, top, Y); put(cx + 2, top + 1, Y); rect(cx, top + 2, cx + 1, top + 2, Y); put(cx, top + 3, Y); put(cx, top + 5, Y)
    elif o == 'HP Bar':
        rect(cx - 4, top + 1, cx + 5, top + 2, (60, 200, 80)); rect(cx + 3, top + 1, cx + 5, top + 2, (200, 60, 60))
    elif o == 'Zzz':
        rect(cx + 3, top, cx + 5, top, W); put(cx + 4, top + 1, W); rect(cx + 3, top + 2, cx + 5, top + 2, W); rect(cx + 6, top + 3, cx + 7, top + 3, W); put(cx + 6, top + 4, W); put(cx + 7, top + 4, W)
    elif o == 'Heart':
        H = (240, 70, 100); put(cx - 1, top, H); put(cx + 2, top, H); rect(cx - 2, top + 1, cx + 3, top + 2, H); rect(cx - 1, top + 3, cx + 2, top + 3, H); rect(cx, top + 4, cx + 1, top + 4, H)
    elif o == 'Speech ...':
        rect(cx + 3, top, cx + 10, top + 3, W); put(cx + 4, top + 4, W); put(cx + 4, top + 2, K); put(cx + 6, top + 2, K); put(cx + 8, top + 2, K)
    elif o == 'Level Up':
        A = (120, 255, 140); put(cx, top, A); put(cx + 1, top, A); rect(cx - 1, top + 1, cx + 2, top + 1, A); rect(cx - 2, top + 2, cx + 3, top + 2, A); rect(cx, top + 3, cx + 1, top + 5, A)

    # outline: empty pixels adjacent to filled -> outline colour
    filled = [[g[y][x] is not None for x in range(N)] for y in range(N)]
    for y in range(N):
        for x in range(N):
            if not filled[y][x]:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < N and 0 <= yy < N and filled[yy][xx]:
                        g[y][x] = K; break

    # background with pattern
    rnd = random.Random(t['seed'])
    img = Image.new('RGB', (N, N), bg)
    px = img.load()
    for y in range(N):
        for x in range(N):
            c = bg
            if bgname == 'Glitch' and rnd.random() < 0.08: c = rnd.choice([(255, 0, 200), (0, 255, 220), (40, 40, 60)])
            px[x, y] = c
    for _ in range(14):
        x, y = rnd.randrange(N), rnd.randrange(N)
        if bgname in ('Town Grass',): px[x, y] = det; px[min(N-1, x+1), y] = det
        elif bgname in ('Night Sky', 'Snowfield', 'Gold Vault'): px[x, y] = det
        elif bgname in ('Dungeon Stone',): px[x, y] = det
        elif bgname in ('Desert Sand', 'Ocean', 'Lava'): px[x, y] = det; px[min(N-1, x+1), y] = det
    if bgname == 'Dungeon Stone':
        for y in range(0, N, 6):
            for x in range(N): px[x, y] = det
    if bgname == 'Night Sky':
        for (x, y) in ((3, 3), (4, 3), (3, 4), (2, 2), (2, 5)): pass
        for (x, y) in ((3, 2), (2, 3), (2, 4), (3, 5), (4, 5)): px[x, y] = (250, 240, 170)
    for y in range(N):
        for x in range(N):
            if g[y][x] is not None: px[x, y] = g[y][x]
    return img.resize((N * SCALE, N * SCALE), Image.NEAREST)

ORDER = ['Background', 'Skin', 'Hoodie', 'Head', 'Eyes', 'Mouth', 'Item', 'Overhead']
TABLE = dict(Background=BG, Skin=SKIN, Hoodie=HOODIE, Head=HEAD, Eyes=EYES, Mouth=MOUTH, Item=ITEM, Overhead=OVER)

seen = set(); items = []
while len(items) < 5000:
    t = {k: pick(TABLE[k]) for k in ORDER}
    key = tuple(t[k] for k in ORDER)
    if key in seen: continue
    seen.add(key); items.append(t)

# rarity score: sum of -log(p)
import math
prob = {k: {n: v[0] / sum(x[0] for x in TABLE[k].values()) for n, v in TABLE[k].items()} for k in ORDER}
for t in items:
    t['score'] = sum(-math.log(prob[k][t[k]]) for k in ORDER)
ranked = sorted(range(5000), key=lambda i: -items[i]['score'])
for r, i in enumerate(ranked, 1): items[i]['rank'] = r
def tier(r):
    return 'Legendary' if r <= 50 else 'Epic' if r <= 250 else 'Rare' if r <= 750 else 'Uncommon' if r <= 2000 else 'Common'

for i, t in enumerate(items, 1):
    t['seed'] = i
    t['Tier'] = tier(t['rank'])
    make(t).save(f'{OUT}/images/{i}.png', optimize=True)
    meta = {'name': f'NPCSHOOD #{i}', 'description': 'NPCSHOOD: 5,000 pixel NPCs in hoodies. They were background characters. Now they\'re yours.',
            'image': f'ipfs://<CID>/{i}.png',
            'attributes': [{'trait_type': k, 'value': t[k]} for k in ORDER] + [{'trait_type': 'Tier', 'value': t['Tier']}, {'trait_type': 'Rank', 'value': t['rank']}]}
    json.dump(meta, open(f'{OUT}/metadata/{i}.json', 'w'), indent=1)
json.dump([{**{k: t[k] for k in ORDER}, 'Tier': t['Tier'], 'Rank': t['rank']} for t in items], open(f'{OUT}/all.json', 'w'))
print('done', len(seen))
