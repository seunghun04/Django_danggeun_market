from django.contrib import admin

from .models import (
    Product,
    Wishlist,
    ChatRoom,
    ChatMessage,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = [
        "id",
        "title",
        "seller",
        "region",
        "price",
        "negotiable",
        "view_count",
        "created_at",
    ]

    search_fields = [
        "title",
        "content",
        "seller__username",
        "region",
    ]

    list_filter = [
        "negotiable",
        "region",
        "created_at",
    ]


admin.site.register(Wishlist)
admin.site.register(ChatRoom)
admin.site.register(ChatMessage)

# Register your models here.
