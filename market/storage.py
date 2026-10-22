import os
import uuid

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

BUCKET_NAME = "product-images"


def upload_product_image(uploaded_file, user_id):

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase 환경변수가 설정되지 않았습니다.")

    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

    extension = uploaded_file.name.split(".")[-1].lower()

    file_name = f"{uuid.uuid4().hex}.{extension}"

    file_path = f"products/{user_id}/{file_name}"

    supabase.storage.from_(BUCKET_NAME).upload(
        path=file_path,
        file=uploaded_file.read(),
        file_options={
            "content-type": uploaded_file.content_type,
            "upsert": "false",
        }
    )

    return supabase.storage.from_(
        BUCKET_NAME
    ).get_public_url(file_path)
