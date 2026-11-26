from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from .models import Profile


class SignUpForm(UserCreationForm):

    name = forms.CharField(
        max_length=100,
        label="이름"
    )

    birth_date = forms.DateField(
        label="생년월일",
        widget=forms.DateInput(
            attrs={
                "type": "date"
            }
        )
    )

    phone = forms.CharField(
        max_length=20,
        label="휴대폰번호"
    )

    class Meta:

        model = User

        fields = [
            "username",
            "name",
            "birth_date",
            "phone",
            "password1",
            "password2",
        ]


    def clean_username(self):

        username = self.cleaned_data.get(
            "username"
        )

        if User.objects.filter(
            username=username
        ).exists():

            raise forms.ValidationError(
                "이미 사용 중인 아이디입니다."
            )

        return username


    def clean_phone(self):

        phone = self.cleaned_data.get(
            "phone"
        )

        if Profile.objects.filter(
            phone=phone
        ).exists():

            raise forms.ValidationError(
                "이미 사용 중인 휴대폰번호입니다."
            )

        return phone


    def save(self, commit=True):

        user = super().save(
            commit=False
        )

        user.first_name = self.cleaned_data[
            "name"
        ]

        if commit:

            user.save()

            Profile.objects.create(
                user=user,
                birth_date=self.cleaned_data[
                    "birth_date"
                ],
                phone=self.cleaned_data[
                    "phone"
                ]
            )

        return user


from django.conf import settings
from .models import Product
from .categories import CHOICE_SEPARATOR, get_form_choices, is_valid_category


class ProductForm(forms.ModelForm):

    # "대분류|소분류" 형식으로 선택 → 저장할 때 두 칸으로 나눠 저장
    category_choice = forms.ChoiceField(
        choices=get_form_choices,
        label="카테고리"
    )

    image = forms.ImageField(
        required=False,
        label="상품 사진"
    )

    class Meta:
        model = Product

        fields = [
            "title",
            "category_choice",
            "content",
            "region",
            "price",
            "negotiable",
            "image",
        ]

        labels = {
            "title": "제목",
            "content": "본문내용",
            "region": "판매 지역",
            "price": "판매 가격",
            "negotiable": "네고 가능",
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # 수정 화면: 기존 카테고리를 선택된 상태로 표시
        if self.instance.pk and self.instance.category:
            self.initial["category_choice"] = (
                f"{self.instance.category}"
                f"{CHOICE_SEPARATOR}"
                f"{self.instance.subcategory}"
            )

    def clean_category_choice(self):

        value = self.cleaned_data.get("category_choice", "")

        category, _, subcategory = value.partition(CHOICE_SEPARATOR)

        if not is_valid_category(category, subcategory):
            raise forms.ValidationError("올바른 카테고리를 선택해 주세요.")

        return value

    def save(self, commit=True):

        product = super().save(commit=False)

        category, _, subcategory = self.cleaned_data[
            "category_choice"
        ].partition(CHOICE_SEPARATOR)

        product.category = category
        product.subcategory = subcategory

        if commit:
            product.save()

        return product

    def clean_image(self):

        image = self.cleaned_data.get("image")

        max_size = getattr(
            settings,
            "MAX_PRODUCT_IMAGE_SIZE",
            10 * 1024 * 1024
        )

        if image and image.size > max_size:
            raise forms.ValidationError(
                f"사진은 {max_size // (1024 * 1024)}MB 이하만 올릴 수 있습니다."
            )

        return image

# =========================================
# 사주 / 오늘의 운세 질문 폼 (DB에 저장하지 않음)
# =========================================

import datetime as _dt


class FortuneForm(forms.Form):

    TOPIC_CHOICES = [
        ("total", "🔮 전체 운세"),
        ("money", "💰 재물운"),
        ("deal", "🤝 거래운"),
        ("love", "💕 애정운"),
        ("work", "📚 일·학업운"),
        ("health", "💪 건강운"),
    ]

    name = forms.CharField(
        max_length=20,
        required=False,
        label="이름 (선택)",
        widget=forms.TextInput(attrs={"placeholder": "예: 폴리"})
    )

    birth_date = forms.DateField(
        label="생년월일 (양력)",
        widget=forms.DateInput(attrs={"type": "date"})
    )

    birth_time = forms.TimeField(
        required=False,
        label="태어난 시간 (모르면 비워두세요)",
        widget=forms.TimeInput(attrs={"type": "time"})
    )

    topic = forms.ChoiceField(
        choices=TOPIC_CHOICES,
        initial="total",
        label="오늘 가장 궁금한 것",
        widget=forms.RadioSelect
    )

    def clean_birth_date(self):

        value = self.cleaned_data["birth_date"]

        if value < _dt.date(1920, 1, 1) or value > _dt.date.today():
            raise forms.ValidationError("1920년 이후, 오늘 이전 날짜를 입력해 주세요.")

        return value
