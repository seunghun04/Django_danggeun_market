from .categories import CATEGORY_TREE, QUICK_CATEGORIES


def categories(request):
    """모든 템플릿에서 상단 카테고리 메뉴를 그릴 수 있도록 목록 전달"""

    return {
        "category_tree": CATEGORY_TREE,
        "quick_categories": QUICK_CATEGORIES,
    }
