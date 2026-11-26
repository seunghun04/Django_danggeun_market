from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from .models import Product, Wishlist, ChatRoom, Profile
from .forms import SignUpForm, ProductForm
from .storage import upload_product_image

from django.shortcuts import   render, redirect

from django.contrib.auth import (
    authenticate,
    login,
    logout,
)

from django.contrib import messages

from .forms import SignUpForm

def state(requset):
    return HttpResponse("server OK", content_type = "text/plain")

def main(request):

    search_query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "latest")

    # 등록된 상품 전체 조회
    products = Product.objects.select_related("seller").all()

    # 검색어가 있으면 필터링
    if search_query:
        products = products.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(region__icontains=search_query)
        )

    # 정렬
    if sort == "popular":
        products = products.order_by(
            "-view_count",
            "-created_at"
        )
    else:
        sort = "latest"
        products = products.order_by("-created_at")

    # 검색된 상품 개수
    product_count = products.count()

    # 히어로 영역에 보여줄 최신 상품
    featured_product = (
        Product.objects
        .order_by("-created_at")
        .first()
    )

    return render(
        request,
        "market/main.html",
        {
            "products": products,
            "product_count": product_count,
            "featured_product": featured_product,
            "q": search_query,
            "sort": sort,
        }
    )



def signup(request):

    if request.user.is_authenticated:
        return redirect("main")

    if request.method == "POST":

        form = SignUpForm(request.POST)

        if form.is_valid():

            user = form.save()

            login(
                request,
                user
            )

            return redirect("main")

    else:
        form = SignUpForm()

    return render(
        request,
        "market/signup.html",
        {
            "form": form
        }
    )

def login_view(request):

    if request.user.is_authenticated:

        return redirect(
            "main"
        )


    if request.method == "POST":

        username = request.POST.get(
            "username"
        )

        password = request.POST.get(
            "password"
        )


        user = authenticate(
            request,
            username=username,
            password=password
        )


        if user is not None:

            login(
                request,
                user
            )

            return redirect(
                "main"
            )


        messages.error(
            request,
            "아이디 또는 비밀번호가 올바르지 않습니다."
        )


    return render(
        request,
        "market/login.html"
    )

def logout_view(request):

    if request.method == "POST":
        logout(request)

    return redirect("main")

def product_list(request):
    products = Product.objects.select_related("seller").all()

    return render(
        request,
        "market/product_list.html",
        {"products": products}
    )


@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user

            image = form.cleaned_data.get("image")

            if image:
                product.image_url = upload_product_image(
                    image,
                    request.user.id
                )

            product.save()

            return redirect(
                "product_detail",
                product_id=product.id
            )
    else:
        form = ProductForm()

    return render(
        request,
        "market/product_form.html",
        {
            "form": form,
            "page_title": "중고상품 등록"
        }
    )


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    Product.objects.filter(id=product.id).update(
        view_count=F("view_count") + 1
    )

    product.refresh_from_db(fields=["view_count"])

    is_wished = False

    if request.user.is_authenticated:
        is_wished = Wishlist.objects.filter(
            user=request.user,
            product=product
        ).exists()

    return render(
        request,
        "market/product_detail.html",
        {
            "product": product,
            "is_wished": is_wished
        }
    )


@login_required
def product_update(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id
    )

    if product.seller != request.user:
        raise PermissionDenied

    if request.method == "POST":

        form = ProductForm(
            request.POST,
            request.FILES,
            instance=product
        )

        if form.is_valid():

            product = form.save(
                commit=False
            )

            image = form.cleaned_data.get(
                "image"
            )

            if image:

                product.image_url = (
                    upload_product_image(
                        image,
                        request.user.id
                    )
                )

            product.save()

            return redirect(
                "product_detail",
                product_id=product.id
            )

    else:

        form = ProductForm(
            instance=product
        )

    return render(
        request,
        "market/product_form.html",
        {
            "form": form,
            "page_title": "상품 수정",
        }
    )


@login_required
def product_delete(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id
    )

    if product.seller != request.user:
        raise PermissionDenied

    if request.method == "POST":

        product.delete()

        return redirect(
            "product_list"
        )

    return render(
        request,
        "market/product_delete.html",
        {
            "product": product
        }
    )

@login_required
def chat_list(request):

    rooms = (
        ChatRoom.objects
        .filter(
            Q(seller=request.user)
            |
            Q(buyer=request.user)
        )
        .select_related(
            "product",
            "seller",
            "buyer"
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "market/chat_list.html",
        {
            "rooms": rooms
        }
    )

@login_required
def wishlist_toggle(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id
    )

    if product.seller == request.user:

        return redirect(
            "product_detail",
            product_id=product.id
        )

    if request.method == "POST":

        wishlist, created = (
            Wishlist.objects
            .get_or_create(
                user=request.user,
                product=product
            )
        )

        if not created:
            wishlist.delete()

    return redirect(
        "product_detail",
        product_id=product.id
    )


@login_required
def chat_start(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id
    )

    if product.seller == request.user:

        return redirect(
            "product_detail",
            product_id=product.id
        )

    room, created = (
        ChatRoom.objects
        .get_or_create(
            product=product,
            buyer=request.user,
            defaults={
                "seller": product.seller
            }
        )
    )

    return redirect(
        "chat_room",
        room_id=room.id
    )

@login_required
def chat_room(request, room_id):

    room = get_object_or_404(
        ChatRoom.objects.select_related(
            "product",
            "seller",
            "buyer"
        ),
        id=room_id
    )

    if (
        request.user != room.seller
        and
        request.user != room.buyer
    ):
        raise PermissionDenied

    chat_messages = (
        room.messages
        .select_related("sender")
        .all()
    )

    return render(
        request,
        "market/chat_room.html",
        {
            "room": room,
            "chat_messages": chat_messages,
        }
    )


# =========================================
# 마이페이지 (번개장터 '내 상점' 형식)
# - DB 구조 변경 없이 기존 모델만 조회합니다.
# =========================================

MYPAGE_SORT_OPTIONS = {
    "latest": ("최신순", ["-created_at"]),
    "popular": ("인기순", ["-view_count", "-created_at"]),
    "low": ("낮은 가격순", ["price", "-created_at"]),
    "high": ("높은 가격순", ["-price", "-created_at"]),
}


@login_required
def mypage(request):

    user = request.user

    # 탭: selling(판매상품) / wishlist(찜한 상품)
    tab = request.GET.get("tab", "selling")
    if tab not in ("selling", "wishlist"):
        tab = "selling"

    # 정렬: 잘못된 값이 들어오면 최신순
    sort = request.GET.get("sort", "latest")
    if sort not in MYPAGE_SORT_OPTIONS:
        sort = "latest"

    # 프로필 (관리자 계정처럼 Profile이 없는 사용자도 오류 없이 처리)
    profile = Profile.objects.filter(user=user).first()

    masked_phone = ""
    if profile and profile.phone:
        digits = profile.phone.replace("-", "")
        if len(digits) >= 8:
            masked_phone = f"{digits[:3]}-****-{digits[-4:]}"
        else:
            masked_phone = profile.phone

    # 판매상품 / 찜한 상품 (찜 수, 채팅 수를 한 번에 계산 → N+1 쿼리 방지)
    my_products = Product.objects.filter(seller=user)
    # 주의: filter(wishlists__user=user) 후 Count("wishlists")를 하면
    # 내 찜 1개만 세어지므로, 상품 id 목록(서브쿼리)으로 걸러냅니다.
    wished_products = Product.objects.filter(
        id__in=Wishlist.objects.filter(user=user).values("product_id")
    )

    if tab == "wishlist":
        products = wished_products.select_related("seller")
    else:
        products = my_products

    products = (
        products
        .annotate(
            wish_total=Count("wishlists", distinct=True),
            chat_total=Count("chat_rooms", distinct=True),
        )
        .order_by(*MYPAGE_SORT_OPTIONS[sort][1])
    )

    # 상점 통계
    my_stats = my_products.aggregate(
        total_views=Sum("view_count"),
    )

    stats = {
        "selling_count": my_products.count(),
        "wishlist_count": wished_products.count(),
        "received_wish_count": Wishlist.objects.filter(
            product__seller=user
        ).count(),
        "chat_count": ChatRoom.objects.filter(
            Q(seller=user) | Q(buyer=user)
        ).count(),
        "total_views": my_stats["total_views"] or 0,
    }

    days_since_join = (timezone.now() - user.date_joined).days + 1

    return render(
        request,
        "market/mypage.html",
        {
            "profile": profile,
            "masked_phone": masked_phone,
            "products": products,
            "tab": tab,
            "sort": sort,
            "sort_options": [
                (key, label)
                for key, (label, _) in MYPAGE_SORT_OPTIONS.items()
            ],
            "stats": stats,
            "days_since_join": days_since_join,
        }
    )
