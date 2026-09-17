import os
import traceback
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timezone

# .env faylini yuklash
load_dotenv()

# =============== SUPABASE ULASH ===============
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL yoki SUPABASE_KEY .env faylida topilmadi!")
    raise SystemExit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# =============== FOYDALANUVCHINI SAQLASH ===============
def save_user_from_message(message):
    """aiogram Message obyektidan foydalanuvchini Supabase'ga saqlash/yangilash"""
    user = message.from_user

    user_data = {
        "telegram_id": user.id,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "username": user.username or "",
        "is_bot": user.is_bot,
        "language_code": user.language_code or "",
        "last_activity": datetime.now(timezone.utc).isoformat(),
    }
    return save_user(user_data)


def save_user(user_data: dict):
    """Foydalanuvchini Supabase'ga saqlash yoki yangilash (upsert)"""
    try:
        response = supabase.table("users").upsert(
            user_data,
            on_conflict="telegram_id"
        ).execute()
        print(f"✅ Foydalanuvchi saqlandi: {user_data.get('first_name')} ({user_data.get('telegram_id')})")
        return response.data
    except Exception as e:
        print(f"❌ Foydalanuvchini saqlashda xatolik: {e}")
        traceback.print_exc()
        return None


def get_or_create_user(telegram_id: int, first_name: str = "", username: str = ""):
    """Foydalanuvchini olish, topilmasa yaratish"""
    user = get_user(telegram_id)
    if not user:
        user_data = {
            "telegram_id": telegram_id,
            "first_name": first_name or "Noma'lum",
            "last_name": "",
            "username": username or "",
            "is_bot": False,
            "language_code": "",
            "last_activity": datetime.now(timezone.utc).isoformat(),
        }
        save_user(user_data)
        user = get_user(telegram_id)
    return user


# =============== FOYDALANUVCHINI O'QISH ===============
def get_user(telegram_id):
    """Foydalanuvchi ma'lumotlarini olish"""
    try:
        response = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"❌ Foydalanuvchini o'qishda xatolik: {e}")
        traceback.print_exc()
        return None


def get_all_users():
    """Barcha foydalanuvchilar ro'yxati"""
    try:
        response = supabase.table("users").select("*").order("registered_at", desc=True).execute()
        return response.data
    except Exception as e:
        print(f"❌ Foydalanuvchilarni o'qishda xatolik: {e}")
        traceback.print_exc()
        return []


def get_user_count():
    """Foydalanuvchilar soni"""
    try:
        response = supabase.table("users").select("*", count="exact").execute()
        return response.count
    except Exception as e:
        print(f"❌ Hisoblashda xatolik: {e}")
        traceback.print_exc()
        return 0


# =============== XABARNI SAQLASH ===============
def save_message_to_db(user_id, message_type, content, file_id=None):
    """Xabarni bazaga saqlash"""
    try:
        message_data = {
            "user_id": user_id,
            "message_type": message_type,
            "content": (content or "")[:500],
            "file_id": file_id or "",
        }
        response = supabase.table("messages").insert(message_data).execute()
        return response.data
    except Exception as e:
        print(f"❌ Xabarni saqlashda xatolik: {e}")
        traceback.print_exc()
        return None


def get_user_messages(telegram_id, limit=10):
    """Foydalanuvchining so'nggi xabarlari"""
    try:
        response = supabase.table("messages").select("*") \
            .eq("user_id", telegram_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        print(f"❌ Xabarlarni o'qishda xatolik: {e}")
        traceback.print_exc()
        return []


def get_stats():
    """Bot statistikasi"""
    try:
        users_response = supabase.table("users").select("*", count="exact").execute()
        total_users = users_response.count

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        today_response = supabase.table("users") \
            .select("*", count="exact") \
            .gte("registered_at", today_start) \
            .execute()
        today_users = today_response.count

        messages_response = supabase.table("messages").select("*", count="exact").execute()
        total_messages = messages_response.count

        return {
            "total_users": total_users,
            "today_users": today_users,
            "total_messages": total_messages,
        }
    except Exception as e:
        print(f"❌ Statistikani olishda xatolik: {e}")
        traceback.print_exc()
        return {"total_users": 0, "today_users": 0, "total_messages": 0}


# =============== FOYDALANUVCHINI O'CHIRISH ===============
def delete_user(telegram_id):
    """Foydalanuvchini o'chirish"""
    try:
        supabase.table("messages").delete().eq("user_id", telegram_id).execute()
        response = supabase.table("users").delete().eq("telegram_id", telegram_id).execute()
        return response.data
    except Exception as e:
        print(f"❌ Foydalanuvchini o'chirishda xatolik: {e}")
        traceback.print_exc()
        return None
