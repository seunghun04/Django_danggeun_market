from django.urls import path

from . import views


urlpatterns = [

    path(
        "",
        views.main,
        name="main"
    ),

    # 기존 회원가입 / 로그인 / 로그아웃
    path(
        "signup/",
        views.signup,
        name="signup"
    ),

    path(
        "login/",
        views.login_view,
        name="login"
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),

    # 상품 목록
    path(
        "products/",
        views.product_list,
        name="product_list"
    ),

    # 상품 등록
    path(
        "products/new/",
        views.product_create,
        name="product_create"
    ),

    # 상품 상세
    path(
        "products/<int:product_id>/",
        views.product_detail,
        name="product_detail"
    ),

    # 상품 수정
    path(
        "products/<int:product_id>/edit/",
        views.product_update,
        name="product_update"
    ),

    # 상품 삭제
    path(
        "products/<int:product_id>/delete/",
        views.product_delete,
        name="product_delete"
    ),

    # 찜하기 / 찜 취소
    path(
        "products/<int:product_id>/wishlist/",
        views.wishlist_toggle,
        name="wishlist_toggle"
    ),

    # 판매자와 채팅 시작
    path(
        "products/<int:product_id>/chat/",
        views.chat_start,
        name="chat_start"
    ),

    # 내 채팅 목록
    path(
        "chats/",
        views.chat_list,
        name="chat_list"
    ),

    # 채팅방
    path(
        "chats/<int:room_id>/",
        views.chat_room,
        name="chat_room"
    ),
]
