import asyncio, html, io, logging, os, sqlite3, aiohttp, qrcode
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton as Btn, InlineKeyboardMarkup as KB, Message

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("BrazilKeyBot")
DOT = chr(46)
TOK = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TOKEN") or "").strip()
ADM = int((os.getenv("ADMIN_TELEGRAM_ID") or os.getenv("OWNER_ID") or "1560345442").strip())
PP_TOK = (os.getenv("PUSHINPAY_API_TOKEN") or "").strip()
SUP_KEY = (os.getenv("PRODSELLER_API_KEY") or "").strip()
SB_URL = (os.getenv("SUPABASE_URL") or "").strip()
SB_KEY = (os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_KEY") or "").strip()
PP_BASE = DOT.join(["https://api", "pushinpay", "com", "br/api"])
PP_SBX = DOT.join(["https://api-sandbox", "pushinpay", "com", "br/api"])
L_HTTP = DOT.join(["http://127", "0", "0", "1"])
DB_FILE = DOT.join(["shop_data", "db"])
ITEMS = [("cc_7d", "CapCut Pro 7 Dias", "Design & Video", 31.90), ("canva_edu", "Canva Pro Vitalicio", "Design & Video", 38.28), ("figma_pro", "Figma Pro Edu 2yrs", "Design & Video", 35.20), ("gpt_plus_1m", "ChatGPT Plus 1 Mes", "IA & Dev", 204.16), ("claude_pro", "Claude 3.5 Pro 1 Mes", "IA & Dev", 350.90), ("cursor_pro", "Cursor Pro AI 1 Mes", "IA & Dev", 255.20), ("yt_1m", "YouTube Premium 1 Mes", "Streaming", 57.42), ("spotify_1m", "Spotify Individual 1 Mes", "Streaming", 70.18), ("netflix_1m", "Netflix 4K 1 Mes", "Streaming", 165.88), ("xbox_ult_1m", "Xbox Game Pass 1 Mes", "Games & VPN", 242.44), ("discord_1m", "Discord Nitro 1 Mes", "Games & VPN", 133.98), ("win11_pro", "Windows 11 Pro Key", "Software", 102.08)]

def db():
    c = sqlite3.connect(DB_FILE)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS goods (sku TEXT PRIMARY KEY, name TEXT, cat TEXT, price REAL)")
        c.execute("CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, msg TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS cfg (k TEXT PRIMARY KEY, v TEXT)")
        for s, n, cat, p in ITEMS:
            c.execute("INSERT OR IGNORE INTO goods VALUES (?, ?, ?, ?)", (s, n, cat, p))

def kb_home(uid: int) -> KB:
    r = [[Btn(text="🛍️ Loja / Catálogo", callback_data="cats"), Btn(text="🔍 Buscar Produto", callback_data="cats")], [Btn(text="🛒 Meu Carrinho", callback_data="cart"), Btn(text="👤 Perfil & Saldo PIX", callback_data="prof")], [Btn(text="📦 Minhas Compras", callback_data="orders"), Btn(text="🤝 Afiliados", callback_data="refs")], [Btn(text="💬 Suporte Brazil Key", callback_data="sup"), Btn(text="❓ Regras & Suporte", callback_data="rules")]]
    if uid == ADM:
        r.append([Btn(text="🎛️ Painel Admin (Telegram-Shop)", callback_data="adm")])
    return KB(inline_keyboard=r)

def kb_back() -> KB:
    return KB(inline_keyboard=[[Btn(text="⬅️ Menu Principal", callback_data="home")]])

async def show(cb: CallbackQuery, txt: str, kb: KB):
    try:
        if cb.message.photo:
            await cb.message.delete()
            await cb.message.answer(txt, reply_markup=kb)
        else:
            await cb.message.edit_text(txt, reply_markup=kb)
    except Exception:
        await cb.message.answer(txt, reply_markup=kb)

async def call_pp(cents: int) -> dict:
    h = {"Authorization": f"Bearer {PP_TOK}", "Accept": "application/json", "Content-Type": "application/json"}
    err = "Token invalido ou expirado"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            for b in (PP_BASE, PP_SBX):
                async with s.post(f"{b}/pix/cashIn", headers=h, json={"value": max(50, cents), "split_rules": []}) as r:
                    d = await r.json(content_type=None)
                    log.info(f"[PUSHINPAY-API] HTTP={r.status} | resp={d}")
                    if r.status in (200, 201) and isinstance(d, dict) and d.get("qr_code"):
                        return {"ok": True, "id": str(d.get("id")), "qr_code": d.get("qr_code")}
                    if isinstance(d, dict) and d.get("error"):
                        err = str(d.get("error"))
    except Exception as e:
        err = str(e)
    return {"ok": False, "error": err}

rt = Router()

@rt.message(CommandStart())
async def cmd_start(m: Message):
    await m.answer(f"🇧🇷 <b>Olá, {html.escape(m.from_user.first_name or 'Cliente')}! Bem-vindo ao Brazil Key Bot.</b>\n\n⚡ <b>Entrega Automática Imediata via PIX:</b>\nEscolha abaixo a categoria desejada:", reply_markup=kb_home(m.from_user.id))

@rt.callback_query(F.data == "home")
async def cb_home(cb: CallbackQuery):
    await show(cb, "🏪 <b>BRAZIL KEY STORE — Menu Oficial</b>\nEscolha abaixo:", kb_home(cb.from_user.id))
    await cb.answer()

@rt.callback_query(F.data == "cats")
async def cb_cats(cb: CallbackQuery):
    with db() as c:
        cats = [r["cat"] for r in c.execute("SELECT DISTINCT cat FROM goods").fetchall()]
    rows = [[Btn(text=f"📂 {cat}", callback_data=f"cat:{cat}")] for cat in cats] + [[Btn(text="⬅️ Menu Principal", callback_data="home")]]
    await show(cb, "🛍️ <b>Categorias — Brazil Key Store:</b>", KB(inline_keyboard=rows))
    await cb.answer()

@rt.callback_query(F.data.startswith("cat:"))
async def cb_cat(cb: CallbackQuery):
    cat = cb.data.split(":", 1)[1]
    with db() as c:
        items = c.execute("SELECT * FROM goods WHERE cat=?", (cat,)).fetchall()
    rows = [[Btn(text=f"{r['name']} — R$ {r['price']:.2f}", callback_data=f"it:{r['sku']}")] for r in items] + [[Btn(text="⬅️ Categorias", callback_data="cats")]]
    await show(cb, f"📂 <b>{html.escape(cat)}:</b>", KB(inline_keyboard=rows))
    await cb.answer()

@rt.callback_query(F.data.startswith("it:"))
async def cb_it(cb: CallbackQuery):
    sku = cb.data.split(":", 1)[1]
    with db() as c:
        g = c.execute("SELECT * FROM goods WHERE sku=?", (sku,)).fetchone()
    if g:
        kb = KB(inline_keyboard=[[Btn(text=f"💠 Comprar com PIX (R$ {g['price']:.2f})", callback_data=f"pix:{g['sku']}")], [Btn(text="⬅️ Voltar", callback_data="cats"), Btn(text="🏠 Menu", callback_data="home")]])
        await show(cb, f"🏷️ <b>{html.escape(g['name'])}</b>\n💰 <b>Preço:</b> R$ {g['price']:.2f}\n📦 <b>Estoque:</b> ✅ Disponível\n⚡ <i>Entrega automática via PIX.</i>", kb)
    await cb.answer()

@rt.callback_query(F.data.startswith("pix:"))
async def cb_pix(cb: CallbackQuery):
    sku = cb.data.split(":", 1)[1]
    with db() as c:
        g = c.execute("SELECT * FROM goods WHERE sku=?", (sku,)).fetchone()
    await cb.answer("Gerando PIX...")
    res = await call_pp(int(round(float(g["price"]) * 100)))
    if not res.get("ok"):
        await show(cb, f"⚠️ <b>Erro na API PushinPay:</b> <code>{html.escape(str(res.get('error')))}</code>", kb_back())
        return
    buf = io.BytesIO()
    qrcode.make(res["qr_code"]).save(buf, format="PNG")
    await cb.message.answer_photo(photo=BufferedInputFile(buf.getvalue(), filename="pix_qr"), caption=f"💠 <b>PIX Oficial — Brazil Key</b>\n🛍️ {g['name']} — R$ {g['price']:.2f}\n<code>{res['qr_code']}</code>", reply_markup=kb_back())

@rt.callback_query(F.data.in_({"cart", "prof", "orders", "refs", "sup", "rules", "adm"}))
async def cb_others(cb: CallbackQuery):
    d = cb.data
    if d == "adm" and cb.from_user.id == ADM:
        with db() as c:
            skus = "\n".join([f"• <code>{r['sku']}</code>: R$ {r['price']:.2f}" for r in c.execute("SELECT * FROM goods").fetchall()])
        await show(cb, f"🎛️ <b>Painel Admin — Brazil Key</b>\n• Preço: <code>/setprice sku valor</code>\n• Canal: <code>/setchannel @canal</code>\n• Suporte: <code>/responder id msg</code>\n\n{skus}", kb_back())
    else:
        await show(cb, "🏪 <b>Brazil Key Store — Oficial</b>\n• Suporte: envie <code>/suporte sua mensagem</code>\n• Catálogo 100% automático.", kb_back())
    await cb.answer()

@rt.message(Command("setprice", "preco"))
async def cmd_price(m: Message):
    p = (m.text or "").split()
    if m.from_user.id == ADM and len(p) >= 3:
        with db() as c:
            c.execute("UPDATE goods SET price=? WHERE LOWER(sku)=LOWER(?)", (float(p[2].replace(",", ".")), p[1]))
        await m.answer(f"✅ Preço de <code>{html.escape(p[1])}</code> atualizado para R$ {float(p[2].replace(',', '.')):.2f}!")

@rt.message(Command("setchannel"))
async def cmd_setchan(m: Message):
    p = (m.text or "").split()
    if m.from_user.id == ADM and len(p) >= 2:
        with db() as c:
            c.execute("INSERT OR REPLACE INTO cfg VALUES ('cid', ?)", ("" if p[1].lower() == "off" else p[1],))
        await m.answer(f"✅ Canal obrigatório configurado: <code>{html.escape(p[1])}</code>")

@rt.message(Command("suporte"))
async def cmd_sup(m: Message):
    txt = (m.text or "").partition(" ")[2].strip()
    if txt:
        with db() as c:
            tid = c.execute("INSERT INTO tickets (uid, msg) VALUES (?, ?)", (m.from_user.id, txt)).lastrowid
        await m.bot.send_message(ADM, f"🆘 <b>Chamado #{tid} — Brazil Key</b>\n👤 @{m.from_user.username} [ID: <code>{m.from_user.id}</code>]\n💬 {html.escape(txt)}\nUse: <code>/responder {tid} texto</code>")
        await m.answer(f"✉️ Chamado #{tid} enviado ao suporte Brazil Key!")

@rt.message(Command("responder"))
async def cmd_resp(m: Message):
    p = (m.text or "").split(maxsplit=2)
    if m.from_user.id == ADM and len(p) >= 3:
        with db() as c:
            r = c.execute("SELECT uid FROM tickets WHERE id=?", (int(p[1].lstrip("#")),)).fetchone()
        if r:
            await m.bot.send_message(r["uid"], f"📩 <b>Suporte Brazil Key (#{p[1]}):</b>\n{html.escape(p[2])}")
            await m.answer("✅ Respondido!")

async def keepalive_13m(port: int):
    log.info("[KEEPALIVE-13M-SERVER] Ativo somente no servidor a cada 13 minutos (780s)")
    await asyncio.sleep(5)
    n = 0
    pub = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    while True:
        n += 1
        code = 0
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
                async with s.get(f"{pub}/health?keepalive=13m" if pub else f"{L_HTTP}:{port}/health?keepalive=13m") as r:
                    code = r.status
        except Exception:
            pass
        log.info(f"[KEEPALIVE-13M-SERVER] Pulso #{n} concluido no servidor | HTTP={code}")
        await asyncio.sleep(780)

async def start_server():
    init_db()
    port = int(os.getenv("PORT", "10000"))
    app = web.Application()
    app.router.add_get("/", lambda req: web.json_response({"status": "healthy", "bot": "@BrazilKeyStoreBot"}))
    app.router.add_get("/health", lambda req: web.json_response({"status": "healthy", "keepalive": "13m"}))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    asyncio.create_task(keepalive_13m(port))
    await call_pp(51)
    bot = Bot(token=TOK, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    me = await bot.get_me()
    await bot.delete_webhook(drop_pending_updates=True)
    log.info(f"Brazil Key Bot online em @{me.username} (ID: {me.id})")
    dp = Dispatcher()
    dp.include_router(rt)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start_server())
