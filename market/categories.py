"""
Poly Market 상품 카테고리 목록 (대분류 → 소분류)

- 카테고리를 추가/수정하려면 이 파일만 고치면 됩니다.
- DB에는 대분류 이름(category)과 소분류 이름(subcategory)이 글자로 저장됩니다.
  이미 등록된 상품의 이름이 바뀌지 않도록, 기존 이름은 가급적 바꾸지 마세요.
"""

CATEGORY_TREE = [
    ("여성의류", ["아우터", "상의", "바지", "치마", "원피스", "기타"]),
    ("남성의류", ["아우터", "상의", "바지", "정장", "기타"]),
    ("신발", ["운동화", "구두", "샌들/슬리퍼", "부츠", "기타"]),
    ("가방/지갑", ["여성가방", "남성가방", "여행용 가방", "여성지갑", "남성지갑", "기타 지갑"]),
    ("시계/쥬얼리", ["시계", "반지", "목걸이", "귀걸이", "기타"]),
    ("디지털", ["휴대폰", "태블릿", "노트북/PC", "카메라", "음향기기", "게임기", "기타"]),
    ("가전제품", ["생활가전", "주방가전", "미용가전", "기타"]),
    ("스포츠/레저", ["자전거", "골프", "캠핑", "헬스/요가", "기타"]),
    ("도서/티켓/문구", ["도서", "티켓", "문구", "기타"]),
    ("가구/인테리어", ["가구", "인테리어 소품", "조명", "기타"]),
    ("생활/주방용품", ["주방용품", "생활용품", "기타"]),
    ("뷰티/미용", ["스킨케어", "메이크업", "향수", "기타"]),
    ("유아동", ["유아의류", "장난감", "유아용품", "기타"]),
    ("반려동물용품", ["강아지용품", "고양이용품", "기타"]),
    ("기타", ["기타"]),
]

# 상단 카테고리 바에 바로 보여줄 대분류
QUICK_CATEGORIES = ["여성의류", "남성의류", "디지털", "스포츠/레저", "가구/인테리어"]

# 상품 폼 선택칸 값의 구분 기호 (예: "가방/지갑|여성가방")
CHOICE_SEPARATOR = "|"


def get_subcategories(category):
    """대분류 이름으로 소분류 목록을 찾습니다. 없으면 None"""
    for name, subs in CATEGORY_TREE:
        if name == category:
            return subs
    return None


def is_valid_category(category, subcategory=""):
    subs = get_subcategories(category)
    if subs is None:
        return False
    return not subcategory or subcategory in subs


def get_form_choices():
    """상품 등록 폼의 카테고리 선택칸 (대분류별로 묶음)"""
    choices = [("", "카테고리를 선택하세요")]
    for name, subs in CATEGORY_TREE:
        choices.append((
            name,
            [(f"{name}{CHOICE_SEPARATOR}{sub}", sub) for sub in subs],
        ))
    return choices
