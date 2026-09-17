import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

import db  # <-- barcha baza funksiyalari shu yerdan keladi

# =============== LOGLARNI YOQISH ===============
logging.basicConfig(level=logging.INFO)

# =============== .env faylini yuklash ===============
load_dotenv()

# =============== BOT KONFIG ===============
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN or not ADMIN_ID:
    print("❌ BOT_TOKEN yoki ADMIN_ID .env faylida topilmadi!")
    raise SystemExit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =============== HOLATLAR ===============
reply_context = {}


# =============== UPTIMEROBOT UCHUN KICHIK VEB-SERVER ===============
async def health_check(request):
    """UptimeRobot shu manzilga ping yuborib turadi, bot uxlab qolmasligi uchun"""
    return web.Response(text="Bot ishlab turibdi ✅")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Health-check server {PORT}-portda ishga tushdi")


# =============== JAVOB TUGMASI ===============
def get_reply_button(user_id: int, message_id: int):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✍️ Javob berish",
                    callback_data=f"reply_{user_id}_{message_id}"
                )
            ]
        ]
    )
    return keyboard


# =============== BOT HANDLERLAR ===============

@dp.message(CommandStart())
async def start_command(message: Message):
    """Start komandasi"""
    try:
        result = db.save_user_from_message(message)
        if result is None:
            print(f"⚠️ Diqqat: {message.from_user.id} saqlanmadi, yuqoridagi xatoga qarang.")
    except Exception as e:
        print(f"❌ Startda xatolik: {e}")

    text = """
👋 Assalomu alaykum!

🤖 Botimizga xush kelibsiz!

Bu bot Muhammadyusufning shaxsiy yordamchisi sifatida ishlaydi.

📌 Ushbu bot orqali siz:

📩 Muhammadyusufga kimligingiz sir saqlangan holda anonim xabar yuborishingiz mumkin.
🖼 Rasm yuborishingiz mumkin.
🎥 Video yuborishingiz mumkin.
🎙 Ovozli xabar (Voice) yuborishingiz mumkin.
🎵 Audio fayl yuborishingiz mumkin.
📄 Hujjat (Document) yuborishingiz mumkin.
❓ Muhammadyusufga savol yuborishingiz mumkin.
💬 Taklif, fikr va mulohazalaringizni yozishingiz mumkin.

🔒 Siz yuborgan ma'lumotlar faqat Muhammadyusufga yetkaziladi.

😊 Botdan bemalol foydalaning!

💙 E'tiboringiz uchun rahmat!
   """
    await message.answer(text)


@dp.message(F.from_user.id != ADMIN_ID)
async def handle_all_messages(message: Message):
    """Barcha xabarlarni qabul qilish va adminga yuborish (admin bundan mustasno)"""
    user = message.from_user

    try:
        result = db.save_user_from_message(message)
        if result is None:
            print(f"⚠️ Diqqat: {user.id} saqlanmadi, yuqoridagi xatoga qarang.")
    except Exception as e:
        print(f"❌ Foydalanuvchini saqlashda xatolik: {e}")

    message_type = "text"
    content = message.text or ""
    file_id = None

    if message.photo:
        message_type = "photo"
        file_id = message.photo[-1].file_id
        content = "📸 Rasm"
    elif message.video:
        message_type = "video"
        file_id = message.video.file_id
        content = "🎥 Video"
    elif message.audio:
        message_type = "audio"
        file_id = message.audio.file_id
        content = "🎵 Audio"
    elif message.voice:
        message_type = "voice"
        file_id = message.voice.file_id
        content = "🎙 Ovoz"
    elif message.document:
        message_type = "document"
        file_id = message.document.file_id
        content = f"📄 {message.document.file_name}"

    try:
        db.save_message_to_db(user.id, message_type, content, file_id)
    except Exception as e:
        print(f"❌ Xabarni saqlashda xatolik: {e}")

    # Foydalanuvchining ism va usernameini xabarga qo'shib beramiz,
    # shunda admin javob berayotganda kimga yozayotganini ko'radi
    display_name = user.first_name or "Noma'lum"
    username_line = f"@{user.username}" if user.username else "yo'q"

    user_info = f"""
👤 **Yangi xabar!**

🙍 **Ism:** {display_name}
🔗 **Username:** {username_line}
🆔 **Telegram ID:** `{user.id}`
📝 **Xabar turi:** {message_type}
    """

    try:
        reply_markup = get_reply_button(user.id, message.message_id)

        if message_type == "text":
            await bot.send_message(
                ADMIN_ID,
                f"{user_info}\n\n📝 {message.text}",
                reply_markup=reply_markup
            )
        else:
            await bot.copy_message(
                chat_id=ADMIN_ID,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            await bot.send_message(
                ADMIN_ID,
                user_info,
                reply_markup=reply_markup
            )

        await message.answer("✅ Xabaringiz muvaffaqiyatli yuborildi! 🙏")
    except Exception as e:
        await message.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
        print(f"❌ Xabarni yuborishda xatolik: {e}")


# =============== JAVOB BERISH (CALLBACK) ===============
@dp.callback_query(lambda c: c.data.startswith("reply_"))
async def handle_reply_callback(callback_query: CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("❌ Bu tugma faqat admin uchun!", show_alert=True)
        return

    try:
        data = callback_query.data.split("_")
        user_id = int(data[1])
        message_id = int(data[2])
    except Exception:
        await callback_query.answer("❌ Xatolik yuz berdi!", show_alert=True)
        return

    # Bazaga murojaat qilinmaydi — user_id callback_data ichida allaqachon bor
    await callback_query.message.reply(
        f"✍️ Foydalanuvchiga javob yozing:\n"
        f"🆔 ID: `{user_id}`\n\n"
        f"💡 Javobingizni shu xabarga yozing va yuboring.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_{user_id}")]
            ]
        )
    )

    reply_context[callback_query.from_user.id] = {
        "target_user_id": user_id
    }

    await callback_query.answer("✅ Javob yozishga tayyormiz!")


# =============== BEKOR QILISH ===============
@dp.callback_query(lambda c: c.data.startswith("cancel_"))
async def handle_cancel_callback(callback_query: CallbackQuery):
    if callback_query.from_user.id in reply_context:
        del reply_context[callback_query.from_user.id]

    await callback_query.message.delete()
    await callback_query.answer("❌ Javob berish bekor qilindi!")


# =============== ADMINGA KELGAN XABARLAR (JAVOB) ===============
@dp.message(F.from_user.id == ADMIN_ID)
async def handle_admin_reply(message: Message):
    if message.from_user.id not in reply_context:
        await message.reply("❌ Hozirda hech kimga javob yozmayapsiz. Avval 'Javob berish' tugmasini bosing!")
        return

    context = reply_context[message.from_user.id]
    target_user_id = context["target_user_id"]

    try:
        if message.text:
            await bot.send_message(
                target_user_id,
                f"📩 **Admin dan javob:**\n\n{message.text}"
            )
        elif message.photo:
            await bot.send_photo(
                target_user_id,
                message.photo[-1].file_id,
                caption=f"📩 **Admin dan javob:**\n\n{message.caption or ''}"
            )
        elif message.document:
            await bot.send_document(
                target_user_id,
                message.document.file_id,
                caption=f"📩 **Admin dan javob:**\n\n{message.caption or ''}"
            )
        else:
            await message.reply("❌ Bu turdagi xabarni yuborib bo'lmaydi!")
            return

        await message.reply(f"✅ Javob (ID: `{target_user_id}`) ga muvaffaqiyatli yuborildi!")
        del reply_context[message.from_user.id]

    except Exception as e:
        await message.reply(f"❌ Xatolik: {e}")
        print(f"❌ Javob yuborishda xatolik: {e}")


# =============== BOTNI ISHGA TUSHIRISH ===============

async def start_bot():
    print("🚀 Bot ishga tushmoqda...")
    print(f"👨‍💼 Admin ID: {ADMIN_ID}")
    print("-" * 40)
    await start_web_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("❌ Bot to'xtatildi!")
    except Exception as e:
        print(f"❌ Bot ishga tushmadi: {e}")
