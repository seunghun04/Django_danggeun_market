"""
만세력 기반 사주팔자 계산 + 오늘의 운세 (재미용)

외부 라이브러리 없이 계산합니다.
- 연주/월주: 태양의 위치(황경)로 절기를 계산 (입춘 = 315°, 이후 30°마다 다음 달)
- 일주: 60갑자 순환 (2000-01-01 = 무오일 기준과 일치하는 율리우스일 공식)
- 시주: 한국에서 흔히 쓰는 30분 보정 시간 (자시 23:30 ~ 01:29)

※ 1954~1961년 표준시 변경, 서머타임(1948~51, 1955~60, 1987~88)은 반영하지 않습니다.
※ 운세 문구는 재미를 위한 것입니다.
"""

import math
import random
from datetime import date, datetime, timedelta

STEMS = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
STEMS_HANJA = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
BRANCHES = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
BRANCHES_HANJA = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
ZODIAC = ["쥐", "소", "호랑이", "토끼", "용", "뱀", "말", "양", "원숭이", "닭", "개", "돼지"]

# 오행: 0 목, 1 화, 2 토, 3 금, 4 수
ELEMENTS = [
    {"name": "목", "hanja": "木", "color": "초록색", "hex": "#4caf6a", "direction": "동쪽", "numbers": [3, 8], "season": "봄"},
    {"name": "화", "hanja": "火", "color": "빨간색", "hex": "#ef5a3c", "direction": "남쪽", "numbers": [2, 7], "season": "여름"},
    {"name": "토", "hanja": "土", "color": "노란색", "hex": "#d9a43a", "direction": "중앙", "numbers": [5, 10], "season": "환절기"},
    {"name": "금", "hanja": "金", "color": "흰색", "hex": "#9aa3ad", "direction": "서쪽", "numbers": [4, 9], "season": "가을"},
    {"name": "수", "hanja": "水", "color": "검정·남색", "hex": "#3d6fb6", "direction": "북쪽", "numbers": [1, 6], "season": "겨울"},
]

STEM_ELEMENT = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
BRANCH_ELEMENT = [4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4]

# 시진 (한국 표준시 기준 30분 보정): 자시 23:30~01:29, 축시 01:30~03:29 ...
HOUR_LABELS = [
    "자시 (23:30~01:29)", "축시 (01:30~03:29)", "인시 (03:30~05:29)",
    "묘시 (05:30~07:29)", "진시 (07:30~09:29)", "사시 (09:30~11:29)",
    "오시 (11:30~13:29)", "미시 (13:30~15:29)", "신시 (15:30~17:29)",
    "유시 (17:30~19:29)", "술시 (19:30~21:29)", "해시 (21:30~23:29)",
]


# -----------------------------------------
# 천문 계산
# -----------------------------------------

def _julian_day(dt_utc):
    """UTC 날짜/시간 → 율리우스일"""
    y, m = dt_utc.year, dt_utc.month
    d = (
        dt_utc.day
        + (dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600) / 24
    )
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def sun_longitude(dt_utc):
    """태양 겉보기 황경(도). 오차 약 0.01° (≈ 15분)"""
    t = (_julian_day(dt_utc) - 2451545.0) / 36525
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = math.radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    c = (
        (1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m)
        + (0.019993 - 0.000101 * t) * math.sin(2 * m)
        + 0.000289 * math.sin(3 * m)
    )
    omega = math.radians(125.04 - 1934.136 * t)
    return (l0 + c - 0.00569 - 0.00478 * math.sin(omega)) % 360


def _jdn(d):
    """그레고리력 날짜 → 율리우스 적일(정수)"""
    a = (14 - d.month) // 12
    y = d.year + 4800 - a
    m = d.month + 12 * a - 3
    return d.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def day_pillar_index(d):
    """60갑자 번호 (0 = 갑자)"""
    return (_jdn(d) + 49) % 60


# -----------------------------------------
# 사주팔자
# -----------------------------------------

def _pillar(stem, branch):
    return {
        "stem": stem,
        "branch": branch,
        "text": STEMS[stem] + BRANCHES[branch],
        "hanja": STEMS_HANJA[stem] + BRANCHES_HANJA[branch],
        "stem_element": STEM_ELEMENT[stem],
        "branch_element": BRANCH_ELEMENT[branch],
        "stem_color": ELEMENTS[STEM_ELEMENT[stem]]["hex"],
        "branch_color": ELEMENTS[BRANCH_ELEMENT[branch]]["hex"],
    }


def hour_branch(hour, minute):
    """한국식 30분 보정 시진 번호 (0 = 자시)"""
    total = (hour * 60 + minute + 30) % 1440  # 23:30 → 0
    return total // 120


def calc_saju(birth_date, birth_time=None):
    """
    birth_date: 양력 생년월일 (date)
    birth_time: 태어난 시각 (time) 또는 None(모름)
    """

    # 시간을 모르면 절기 계산에 정오를 사용
    clock = birth_time or datetime.min.time().replace(hour=12)
    local_dt = datetime.combine(birth_date, clock)
    utc_dt = local_dt - timedelta(hours=9)

    # 월: 입춘(315°)부터 30°마다 인월, 묘월 ...
    lon = sun_longitude(utc_dt)
    month_idx = int(((lon - 315) % 360) // 30)  # 0 = 인월

    # 연: 1~2월인데 아직 자월/축월이면 입춘 전 → 전년도
    saju_year = birth_date.year
    if birth_date.month <= 2 and month_idx >= 10:
        saju_year -= 1

    year_stem = (saju_year - 4) % 10
    year_branch = (saju_year - 4) % 12

    first_month_stem = ((year_stem % 5) * 2 + 2) % 10  # 갑·기년 → 병인월
    month_stem = (first_month_stem + month_idx) % 10
    month_branch = (month_idx + 2) % 12

    # 일: 23:30 이후 출생은 다음 날 일주로 계산
    day_date = birth_date
    if birth_time and (birth_time.hour * 60 + birth_time.minute) >= 23 * 60 + 30:
        day_date = birth_date + timedelta(days=1)
    day_idx = day_pillar_index(day_date)
    day_stem, day_branch = day_idx % 10, day_idx % 12

    pillars = {
        "year": _pillar(year_stem, year_branch),
        "month": _pillar(month_stem, month_branch),
        "day": _pillar(day_stem, day_branch),
        "hour": None,
    }

    if birth_time:
        hb = hour_branch(birth_time.hour, birth_time.minute)
        first_hour_stem = (day_stem % 5) * 2 % 10  # 갑·기일 → 갑자시
        pillars["hour"] = _pillar((first_hour_stem + hb) % 10, hb)

    # 오행 개수
    counts = [0] * 5
    for p in pillars.values():
        if p:
            counts[p["stem_element"]] += 1
            counts[p["branch_element"]] += 1

    total = sum(counts)
    element_stats = [
        {
            **ELEMENTS[i],
            "count": counts[i],
            "percent": round(counts[i] / total * 100) if total else 0,
        }
        for i in range(5)
    ]

    weakest = min(range(5), key=lambda i: (counts[i], i))
    strongest = max(range(5), key=lambda i: (counts[i], -i))

    return {
        "pillars": pillars,
        "pillar_list": [
            ("시주", pillars["hour"]),
            ("일주", pillars["day"]),
            ("월주", pillars["month"]),
            ("연주", pillars["year"]),
        ],
        "day_master": day_stem,
        "day_master_name": STEMS[day_stem] + STEMS_HANJA[day_stem],
        "day_master_info": DAY_MASTER_INFO[day_stem],
        "zodiac": ZODIAC[year_branch],
        "elements": element_stats,
        "weakest": ELEMENTS[weakest],
        "strongest": ELEMENTS[strongest],
        "time_known": birth_time is not None,
        "sun_longitude": round(lon, 2),
    }


# -----------------------------------------
# 해석 문구
# -----------------------------------------

DAY_MASTER_INFO = [
    {"image": "🌳 큰 나무", "keyword": "곧음 · 성장 · 리더십",
     "text": "하늘로 곧게 뻗는 큰 나무처럼 목표가 분명하고 추진력이 있어요. 한번 정하면 꾸준히 밀고 나가지만, 가끔은 유연하게 굽힐 줄 알면 더 크게 자랍니다."},
    {"image": "🌿 덩굴·화초", "keyword": "유연함 · 친화력 · 생활력",
     "text": "어디서든 뿌리를 내리는 덩굴처럼 적응력과 친화력이 뛰어나요. 사람 사이에서 길을 찾는 재주가 있고, 섬세하게 실속을 챙기는 타입입니다."},
    {"image": "☀️ 태양", "keyword": "열정 · 표현력 · 낙천",
     "text": "모두를 비추는 태양처럼 밝고 솔직해요. 주변에 에너지를 나눠 주는 분위기 메이커지만, 너무 뜨거워지지 않도록 쉬는 시간도 챙겨 주세요."},
    {"image": "🕯️ 촛불·별빛", "keyword": "섬세함 · 집중력 · 배려",
     "text": "어둠 속 촛불처럼 따뜻하고 세심해요. 한 가지에 깊게 몰입하는 힘이 있고, 가까운 사람을 은근히 잘 챙기는 다정한 타입입니다."},
    {"image": "⛰️ 큰 산", "keyword": "듬직함 · 신뢰 · 포용력",
     "text": "흔들리지 않는 큰 산처럼 믿음직하고 포용력이 커요. 쉽게 움직이지 않는 만큼 결정은 신중하지만, 한번 맺은 인연은 오래 갑니다."},
    {"image": "🌾 기름진 땅", "keyword": "실속 · 성실 · 돌봄",
     "text": "곡식을 길러내는 밭처럼 성실하고 실속 있어요. 남을 돌보고 키워주는 능력이 있고, 차곡차곡 쌓아 올리는 데 강합니다."},
    {"image": "⚔️ 단단한 쇠", "keyword": "결단력 · 의리 · 정의감",
     "text": "단단한 원석처럼 결단력과 의리가 있어요. 옳고 그름이 분명하고 추진력이 강하지만, 말을 조금만 부드럽게 하면 더 많은 사람이 따릅니다."},
    {"image": "💎 보석", "keyword": "감각 · 완벽주의 · 품격",
     "text": "반짝이는 보석처럼 감각이 예리하고 깔끔한 걸 좋아해요. 디테일을 놓치지 않는 완벽주의자지만, 스스로에게는 조금 너그러워져도 괜찮아요."},
    {"image": "🌊 큰 바다", "keyword": "지혜 · 포부 · 자유로움",
     "text": "넓은 바다처럼 생각의 폭이 크고 지혜로워요. 새로운 것에 대한 호기심과 포부가 크고, 어떤 상황에서도 흐름을 읽는 힘이 있습니다."},
    {"image": "💧 이슬비", "keyword": "직관 · 감성 · 차분함",
     "text": "조용히 스며드는 이슬비처럼 차분하고 직관이 뛰어나요. 남의 마음을 잘 읽고, 겉으로 드러내기보다 안에서 깊게 생각하는 타입입니다."},
]

# 오늘 일진과 내 일간의 관계(십신)별 운세
TEN_GOD_FORTUNE = {
    "비견": {
        "score": 72, "title": "든든한 동료의 날",
        "summary": "나와 비슷한 기운이 들어와 자신감이 붙는 날이에요. 혼자보다는 함께할 때 일이 잘 풀립니다.",
        "money": "큰 지출보다는 현상 유지가 좋아요. 친구와 나눠 사면 이득!",
        "love": "편안한 친구 같은 대화가 마음을 열어 줘요.",
        "work": "협업 운이 좋아요. 동료에게 먼저 도움을 청해 보세요.",
        "health": "체력은 괜찮지만 무리한 운동은 피하세요.",
        "deal": "비슷한 물건을 파는 판매자가 많을 수 있어요. 사진을 한 장 더 올려 차별화해 보세요.",
    },
    "겁재": {
        "score": 60, "title": "지갑 단속의 날",
        "summary": "의욕은 넘치지만 경쟁이 붙기 쉬운 날이에요. 욱하는 마음만 다스리면 무난합니다.",
        "money": "충동구매 주의! 장바구니에 담아 두고 하루 뒤에 결정하세요.",
        "love": "자존심 싸움은 금물. 한 발 물러서면 오히려 가까워져요.",
        "work": "경쟁 상황에서 페이스를 지키는 사람이 이깁니다.",
        "health": "급하게 먹거나 서두르다 다치지 않게 조심하세요.",
        "deal": "가격 흥정이 치열할 수 있어요. 최저가 기준선을 미리 정해 두세요.",
    },
    "식신": {
        "score": 88, "title": "복이 굴러오는 날",
        "summary": "여유롭고 즐거운 기운이 가득해요. 맛있는 걸 먹고, 하고 싶은 걸 표현하면 좋은 일이 따라옵니다.",
        "money": "작은 행운이 있는 날. 오래 묵힌 물건이 팔릴 수 있어요.",
        "love": "자연스러운 웃음이 최고의 매력 포인트예요.",
        "work": "아이디어가 술술 나와요. 메모해 두면 큰 자산이 됩니다.",
        "health": "컨디션 좋음! 다만 과식만 조심하세요.",
        "deal": "판매 글 문구가 잘 써지는 날! 상품 설명을 새로 다듬어 보세요.",
    },
    "상관": {
        "score": 70, "title": "말 한마디가 빛나는 날",
        "summary": "표현력과 재치가 폭발하는 날이에요. 다만 말이 앞서면 오해가 생길 수 있으니 한 번 더 생각하고 말하세요.",
        "money": "새로운 시도가 수익으로 이어질 수 있어요.",
        "love": "솔직함은 좋지만 농담의 수위는 조절해요.",
        "work": "기존 방식을 바꿔 보자는 제안이 통할 수 있어요.",
        "health": "생각이 많아 잠이 부족할 수 있어요. 일찍 쉬세요.",
        "deal": "채팅 답장을 친절하게! 말투 하나로 거래가 성사됩니다.",
    },
    "편재": {
        "score": 85, "title": "기회가 들어오는 날",
        "summary": "예상치 못한 기회와 인연이 찾아오는 날이에요. 움직이는 만큼 얻는 게 많습니다.",
        "money": "뜻밖의 수입 운! 안 쓰는 물건을 정리해 올려 보세요.",
        "love": "새로운 만남의 기회가 있어요. 약속은 거절하지 마세요.",
        "work": "넓게 발을 뻗을수록 좋은 결과가 와요.",
        "health": "활동량이 많아지니 물을 자주 마셔 주세요.",
        "deal": "거래운 최고! 오늘 올린 상품은 빨리 팔릴 가능성이 높아요.",
    },
    "정재": {
        "score": 82, "title": "차곡차곡 쌓이는 날",
        "summary": "성실함이 보상받는 안정적인 날이에요. 계획대로 움직이면 실속을 챙길 수 있습니다.",
        "money": "꼼꼼한 비교가 이득으로 이어져요. 가계부를 써 보세요.",
        "love": "작은 약속을 지키는 것이 신뢰를 쌓아요.",
        "work": "마무리 운이 좋아요. 미뤄 둔 일을 끝내세요.",
        "health": "규칙적인 식사와 수면이 행운을 지켜 줘요.",
        "deal": "정가 판매가 잘 되는 날. 무리하게 깎아 주지 않아도 괜찮아요.",
    },
    "편관": {
        "score": 58, "title": "버티면 이기는 날",
        "summary": "압박감이 느껴질 수 있지만, 잘 버티면 한 단계 성장하는 날이에요. 원칙을 지키세요.",
        "money": "보증이나 큰 결제는 미루는 게 좋아요.",
        "love": "상대의 말을 끝까지 들어 주는 게 중요해요.",
        "work": "어려운 과제가 오지만 해내면 인정받아요.",
        "health": "스트레스 관리 필수! 가벼운 산책을 추천해요.",
        "deal": "안전거래 원칙을 꼭 지키세요. 선입금 요구는 조심!",
    },
    "정관": {
        "score": 80, "title": "인정받는 날",
        "summary": "질서와 명예의 기운이 들어오는 날이에요. 바른 행동이 좋은 평판으로 돌아옵니다.",
        "money": "계획된 지출은 OK, 즉흥 지출은 NO.",
        "love": "예의 바른 모습이 호감을 사요.",
        "work": "윗사람·선생님께 칭찬받을 일이 생겨요.",
        "health": "생활 리듬을 지키면 컨디션 좋음.",
        "deal": "약속 시간을 지키는 것만으로 좋은 후기를 받을 수 있어요.",
    },
    "편인": {
        "score": 66, "title": "영감이 번뜩이는 날",
        "summary": "직관과 아이디어가 빛나는 날이에요. 혼자만의 시간이 오히려 좋은 답을 줍니다.",
        "money": "독특한 물건에 눈길이 가요. 취미 관련 지출은 적당히!",
        "love": "말보다 눈빛과 분위기가 통하는 날이에요.",
        "work": "새로운 걸 배우기에 좋아요. 강의·책 추천!",
        "health": "생각이 많아질 수 있어요. 따뜻한 차 한 잔 어떨까요?",
        "deal": "희귀템·수집품 카테고리를 구경해 보세요. 보물을 찾을지도!",
    },
    "정인": {
        "score": 84, "title": "도움받는 날",
        "summary": "주변의 도움과 응원이 들어오는 따뜻한 날이에요. 배움과 문서 운도 좋습니다.",
        "money": "선물이나 혜택이 들어올 수 있어요.",
        "love": "가족·연인에게 마음을 표현하기 좋은 날이에요.",
        "work": "공부·자격증·서류 일이 잘 풀려요.",
        "health": "충분한 휴식이 곧 행운이에요.",
        "deal": "믿을 만한 판매자를 만날 운! 상점 후기를 확인하고 구매해 보세요.",
    },
}

TOPICS = [
    ("total", "총운"),
    ("money", "재물운"),
    ("deal", "거래운"),
    ("love", "애정운"),
    ("work", "일·학업운"),
    ("health", "건강운"),
]

LUCKY_ITEMS = [
    "따뜻한 커피", "이어폰", "손거울", "책 한 권", "운동화",
    "향기 좋은 핸드크림", "작은 화분", "손목시계", "노트와 펜", "에코백",
]

# 육합 / 충 (지지 관계)
SIX_HARMONY = {frozenset(p) for p in [(0, 1), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7)]}


def ten_god(day_master, other_stem):
    """일간 기준 다른 천간의 십신"""
    diff = (STEM_ELEMENT[other_stem] - STEM_ELEMENT[day_master]) % 5
    same = (day_master % 2) == (other_stem % 2)
    names = [
        ("비견", "겁재"), ("식신", "상관"), ("편재", "정재"),
        ("편관", "정관"), ("편인", "정인"),
    ]
    return names[diff][0 if same else 1]


def today_fortune(saju, birth_date, today=None, topic="total"):
    """내 사주 + 오늘 일진으로 오늘의 운세 생성 (같은 사람은 하루 동안 같은 결과)"""

    from .categories import CATEGORY_TREE

    today = today or date.today()

    t_idx = day_pillar_index(today)
    t_stem, t_branch = t_idx % 10, t_idx % 12
    my_stem = saju["day_master"]
    my_branch = saju["pillars"]["day"]["branch"]

    god = ten_god(my_stem, t_stem)
    data = TEN_GOD_FORTUNE[god]

    # 생년월일 + 오늘 날짜로 고정된 난수 → 새로고침해도 같은 결과
    rng = random.Random(f"{birth_date.isoformat()}-{today.isoformat()}")

    # 지지 관계: 합이면 +, 충이면 -
    relation = None
    bonus = 0
    if frozenset((my_branch, t_branch)) in SIX_HARMONY:
        relation = "오늘의 기운과 내 일지가 '합'을 이뤄 인연·협력 운이 좋아요 🤝"
        bonus = 6
    elif (my_branch - t_branch) % 12 == 6:
        relation = "오늘의 기운과 내 일지가 '충'을 이뤄 변화가 많아요. 서두르지 마세요 ⚠️"
        bonus = -7

    def score(base):
        return max(35, min(99, base + bonus + rng.randint(-6, 6)))

    scores = [
        {"key": key, "label": label, "score": score(data["score"])}
        for key, label in TOPICS
    ]

    helper = saju["weakest"]
    lucky_number = rng.choice(helper["numbers"])
    lucky_category = rng.choice(CATEGORY_TREE[:-1])[0]  # '기타' 제외
    lucky_hour = rng.choice(HOUR_LABELS[3:11])

    topic_key = topic if topic in dict(TOPICS) else "total"
    answer = data["summary"] if topic_key == "total" else data[topic_key]

    return {
        "date": today,
        "day_pillar": STEMS[t_stem] + BRANCHES[t_branch] + "일",
        "day_pillar_hanja": STEMS_HANJA[t_stem] + BRANCHES_HANJA[t_branch] + "日",
        "ten_god": god,
        "title": data["title"],
        "summary": data["summary"],
        "details": [(label, data[key] if key != "total" else data["summary"]) for key, label in TOPICS[1:]],
        "topic_label": dict(TOPICS)[topic_key],
        "topic_answer": answer,
        "relation": relation,
        "scores": scores,
        "total_score": scores[0]["score"],
        "lucky": {
            "color": helper["color"],
            "color_hex": helper["hex"],
            "number": lucky_number,
            "direction": helper["direction"],
            "item": rng.choice(LUCKY_ITEMS),
            "category": lucky_category,
            "hour": lucky_hour,
            "element": helper["name"] + "(" + helper["hanja"] + ")",
        },
    }
