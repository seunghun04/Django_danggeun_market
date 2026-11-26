# 상품에 카테고리 칸 2개를 추가합니다.
# - 기존 데이터는 삭제/변경되지 않으며, 기존 상품은 빈 값("") = 미분류가 됩니다.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0002_product_wishlist_chatroom_chatmessage_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='category',
            field=models.CharField(blank=True, db_index=True, default='', max_length=30, verbose_name='카테고리'),
        ),
        migrations.AddField(
            model_name='product',
            name='subcategory',
            field=models.CharField(blank=True, default='', max_length=30, verbose_name='세부 카테고리'),
        ),
    ]
