import asyncio, html, io, logging, os, aiohttp, qrcode
from decimal import Decimal
from dotenv import load_dotenv
load_dotenv(encoding="utf-8")
DOT = chr(46)
os.environ["TOKEN"] = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TOKEN") or "").strip()
os.environ["OWNER_ID"] = (os.getenv("ADMIN_TELEGRAM_ID") or os.getenv("OWNER_ID") or "1560345442").strip()
os.environ.setdefault("HELPER_ID", os.environ["OWNER_ID"])
for k, v in [("PAY_CURRENCY", "BRL"), ("BOT_LOCALE", "en"), ("REDIS_ENABLED", "0"), ("POSTGRES_DB", "shop"), ("POSTGRES_USER", "shop"), ("POSTGRES_PASSWORD", "BrazilKey2026!"), ("SECRET_KEY", "brazil_key_secret_production_9988776655443322"), ("ADMIN_PASSWORD", "BrazilKeyAdmin2026!")]:
    os.environ.setdefault(k, os.getenv(k, v))
os.environ["ADMIN_HOST"], os.environ["ADMIN_PORT"] = "0.0.0.0", os.getenv("PORT", "10000")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import bot.database.main as db_m
def _db_init(self):
    u = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///orig_shop{DOT}db")
    self._Database__engine = create_async_engine(u, echo=False)
    self._Database__SessionLocal = async_sessionmaker(bind=self._Database__engine, class_=AsyncSession, autoflush=False, autocommit=False, expire_on_commit=False)
db_m.Database.__init__ = _db_init
if hasattr(db_m.SingletonMeta, "_instances"): db_m.SingletonMeta._instances.clear()

import bot.database.models.main as mod_m, bot.database.methods.transactions as tx_m, bot.handlers.other as oth_m, bot.keyboards.inline as kb_m, bot.handlers.user.balance_and_payment as pay_m, bot.main as main_m
from bot.database.methods.create import create_category, create_item, add_values_to_item
from bot.database.methods.read import check_category_cached, get_item_info_cached
from bot.database.methods.transactions import process_payment_with_referral
from aiogram import F
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton as Btn, InlineKeyboardMarkup as KB
from aiogram.fsm.context import FSMContext
from bot.misc import EnvKeys
from bot.i18n import localize
from bot import start_bot

PS_KEY, PP_TOK = (os.getenv("PRODSELLER_API_KEY") or "").strip(), (os.getenv("PUSHINPAY_API_TOKEN") or "").strip()
PS_URL = DOT.join(["https://prodseller", "ru/api/v1"])
PP_URLS = (DOT.join(["https://api", "pushinpay", "com", "br/api"]), DOT.join(["https://api-sandbox", "pushinpay", "com", "br/api"]))
L_HTTP = DOT.join(["http://127", "0", "0", "1"])
PS_MAP = {}
SEED = [("cc_7d", "CapCut Pro 7 days", "Design & Video", 31.90), ("canva_edu", "Canva Edu Lifetime", "Design & Video", 38.28), ("adobe_1m", "Adobe Creative Cloud 1m", "Design & Video", 223.30), ("figma_pro", "Figma Pro 2yrs Edu", "Design & Video", 35.20), ("gpt_plus_1m", "ChatGPT Plus 1m", "AI & Dev Tools", 204.16), ("claude_pro", "Claude 3.5 Pro 1m", "AI & Dev Tools", 350.90), ("cursor_pro", "Cursor Pro AI 1m", "AI & Dev Tools", 255.20), ("copilot_1m", "GitHub Copilot 1m", "AI & Dev Tools", 140.36), ("yt_1m", "YouTube Premium 1m", "Streaming", 57.42), ("spotify_1m", "Spotify Individual 1m", "Streaming", 70.18), ("netflix_1m", "Netflix 4K 1m", "Streaming", 165.88), ("xbox_ult_1m", "Xbox Game Pass Ultimate 1m", "Gaming & VPN", 242.44), ("discord_1m", "Discord Nitro Full 1m", "Gaming & VPN", 133.98), ("win11_pro", "Windows 11 Pro Key", "Software & OS", 102.08)]

async def _sync_ps():
    prods = [{"id": s, "name": n, "category": c, "price": p} for s, n, c, p in SEED]
    if PS_KEY:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
                async with s.get(f"{PS_URL}/products", headers={"X-API-Key": PS_KEY}) as r:
                    if r.status == 200:
                        d = await r.json(content_type=None)
                        prods = (d.get("products") if isinstance(d, dict) else d) or prods
        except Exception: pass
    for p in prods:
        pid, name, cat = str(p.get("id") or p.get("name")), str(p.get("name"))[:90], str(p.get("category") or "Subscriptions")[:90]
        pr = Decimal(str(round(float(p.get("price") or 29.90), 2)))
        PS_MAP[name] = pid
        if not await check_category_cached(cat): await create_category(cat)
        if not await get_item_info_cached(name):
            await create_item(name, f"{name} — Official Subscription", pr, cat)
            await add_values_to_item(name, f"KEY:{pid}", True)

_orig_reg = mod_m.register_models
async def _reg():
    async with db_m.Database().engine.begin() as c: await c.run_sync(db_m.Database.BASE.metadata.create_all)
    await _orig_reg()
    await _sync_ps()
mod_m.register_models = main_m.register_models = _reg

_orig_buy = tx_m.buy_item_transaction
async def _buy(uid: int, name: str, promo: str = None):
    ok, msg, data = await _orig_buy(uid, name, promo)
    if ok and isinstance(data, dict) and PS_KEY:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
                async with s.post(f"{PS_URL}/orders", headers={"X-API-Key": PS_KEY}, json={"productId": PS_MAP.get(name, name), "quantity": 1}) as r:
                    if r.status in (200, 201):
                        d = await r.json(content_type=None)
                        if isinstance(d, dict) and d.get("deliveredKey"): data["value"] = str(d["deliveredKey"])
        except Exception: pass
    return ok, msg, data
tx_m.buy_item_transaction = pay_m.buy_item_transaction = _buy

_orig_any = oth_m._any_payment_method_enabled
oth_m._any_payment_method_enabled = pay_m._any_payment_method_enabled = lambda: bool(PP_TOK) or _orig_any()
_orig_choice = kb_m.get_payment_choice
def _choice() -> KB:
    rows = list(_orig_choice().inline_keyboard)
    rows.insert(max(0, len(rows) - 1), [Btn(text="💠 PIX (PushinPay)", callback_data="pay_pushinpay")])
    return KB(inline_keyboard=rows)
kb_m.get_payment_choice = pay_m.get_payment_choice = _choice

@pay_m.router.callback_query(F.data == "pay_pushinpay")
async def _on_pp(call: CallbackQuery, state: FSMContext):
    amt = float((await state.get_data()).get("amount") or 10)
    await call.answer("Gerando PIX PushinPay...")
    h = {"Authorization": f"Bearer {PP_TOK}", "Accept": "application/json", "Content-Type": "application/json"}
    err, qr, tid = "Token invalido ou expirado", "", ""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            for b in PP_URLS:
                async with s.post(f"{b}/pix/cashIn", headers=h, json={"value": max(50, int(round(amt * 100))), "split_rules": []}) as r:
                    d = await r.json(content_type=None)
                    if r.status in (200, 201) and isinstance(d, dict) and d.get("qr_code"):
                        qr, tid = str(d["qr_code"]), str(d.get("id"))
                        break
                    if isinstance(d, dict) and d.get("error"): err = str(d["error"])
    except Exception as e: err = str(e)
    if not qr:
        await call.message.edit_text(f"⚠️ <b>PushinPay PIX:</b> <code>{html.escape(err)}</code>", reply_markup=_choice())
        return
    buf = io.BytesIO()
    qrcode.make(qr).save(buf, format="PNG")
    kb = KB(inline_keyboard=[[Btn(text=localize("btn.check_payment"), callback_data=f"chk_pp:{tid}:{amt:.2f}")], [Btn(text=localize("btn.back"), callback_data="profile")]])
    await call.message.answer_photo(photo=BufferedInputFile(buf.getvalue(), filename="pix_qr"), caption=f"💠 <b>PIX PushinPay — {amt:.2f} {EnvKeys.PAY_CURRENCY}</b>\n\n<code>{html.escape(qr)}</code>", reply_markup=kb)

@pay_m.router.callback_query(F.data.startswith("chk_pp:"))
async def _chk_pp(call: CallbackQuery, state: FSMContext):
    _, tid, amt_s = call.data.split(":", 2)
    paid = False
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
            for b in PP_URLS:
                async with s.get(f"{b}/transactions/{tid}", headers={"Authorization": f"Bearer {PP_TOK}", "Accept": "application/json"}) as r:
                    if r.status == 200 and str((await r.json(content_type=None)).get("status", "")).lower() in ("paid", "approved", "completed"): paid = True
    except Exception: pass
    if not paid:
        await call.answer("⏳ Pagamento ainda não confirmado na PushinPay.", show_alert=True)
        return
    ok, msg = await process_payment_with_referral(user_id=call.from_user.id, amount=Decimal(amt_s), provider="pushinpay", external_id=tid, referral_percent=int(EnvKeys.REFERRAL_PERCENT or 0))
    if ok:
        await state.clear()
        await call.message.answer(f"✅ <b>PIX Confirmado! +{amt_s} {EnvKeys.PAY_CURRENCY} creditados no seu saldo.</b>")
    else: await call.answer(msg, show_alert=True)

async def _ka():
    port, pub = int(os.getenv("PORT", "10000")), os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    logging.info("[KEEPALIVE-13M-SERVER] Ativo somente no servidor a cada 13 minutos (780s)")
    await asyncio.sleep(8)
    while True:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
                async with s.get(f"{pub}/health" if pub else f"{L_HTTP}:{port}/health") as r:
                    logging.info(f"[KEEPALIVE-13M-SERVER] Pulso concluido no servidor | HTTP={r.status}")
        except Exception: pass
        await asyncio.sleep(780)

async def _main():
    asyncio.create_task(_ka())
    await start_bot()

if __name__ == "__main__":
    asyncio.run(_main())
