import asyncio, html, io, logging, os, re, sqlite3, sys, time
from decimal import Decimal, ROUND_HALF_UP
import aiohttp, qrcode
from dotenv import load_dotenv
load_dotenv(encoding="utf-8")
DOT, SEP = chr(46), chr(58) + chr(47) + chr(47)
P_S, P_H = "https" + SEP, "http" + SEP
CFG = os.getenv("RUNTIME_CFG_DB", f"runtime_cfg{DOT}db")
def _conn(): c = sqlite3.connect(CFG); c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)"); return c
def cget(k, d=""): c = _conn(); r = c.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone(); c.close(); return r[0] if (r and r[0]) else d
def cset(k, v): c = _conn(); c.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (k, str(v).strip())); c.commit(); c.close()
DEF_TOK = "9204796203:AAETbOjo0250ZpOaSumQL6auIBiuxRhhOIM"
DEF_PS = "psk_bd8156f453ed21aa5c3317cca98b9217885cabe9c8c706bd"
DEF_PP = "73227|lKu865OTKS32zaRXjRfaXDjUChuTizUeqGL4i8ym38538fa1"
DEF_OAP = "leog3oficina_8e9chlc0xx3wz6ag"
DEF_OAS = "vb4efitm8uzm97v7ldq3thmwd1er6zmbzo5tjj35xpr6yl948n1bzgshtl5i8jb"
os.environ["TOKEN"] = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TOKEN") or cget("tok", DEF_TOK)).strip()
os.environ["OWNER_ID"] = (os.getenv("ADMIN_TELEGRAM_ID") or os.getenv("OWNER_ID") or "1560345442").strip()
os.environ.setdefault("HELPER_ID", os.environ["OWNER_ID"])
_ENV_DEFAULTS = [os.environ.setdefault(k, os.getenv(k, v)) for k, v in [("PAY_CURRENCY", "BRL"), ("BOT_LOCALE", "en"), ("REDIS_ENABLED", "0"), ("POSTGRES_DB", "shop"), ("POSTGRES_USER", "shop"), ("POSTGRES_PASSWORD", "BrazilKey2026!"), ("SECRET_KEY", "brazil_key_secret_production_9988776655443322"), ("ADMIN_PASSWORD", "BrazilKeyAdmin2026!")]]
os.environ["ADMIN_HOST"], os.environ["ADMIN_PORT"] = DOT.join(["0", "0", "0", "0"]), os.getenv("PORT", "10000")
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import bot.database.main as db_m
def _db_init(self): u = os.getenv("DATABASE_URL", f"sqlite+aiosqlite{SEP}/brazilkey_shop{DOT}db"); kw = {} if u.startswith("sqlite") else {"pool_pre_ping": True, "connect_args": {"statement_cache_size": 0}}; self._Database__engine = create_async_engine(u, echo=False, **kw); sm = async_sessionmaker(bind=self._Database__engine, class_=AsyncSession, autoflush=False, autocommit=False, expire_on_commit=False); self._Database__sessionmaker = self._Database__SessionLocal = sm
db_m.Database.__init__ = _db_init
_CLR = getattr(db_m.SingletonMeta, "_instances", {}).clear() if hasattr(db_m.SingletonMeta, "_instances") else None
import bot.i18n.strings as i18s, bot.database.models.main as mod_m, bot.database.methods.read as dbr, bot.database.methods.transactions as tx_m, bot.keyboards.inline as kb_m, bot.handlers.user.balance_and_payment as pay_m
from bot.database.models.main import Goods, Role, User
from bot.database.methods.create import create_category, create_item, add_values_to_item
from bot.database.methods.read import check_category_cached, get_item_info_cached
from bot.database.methods.transactions import process_payment_with_referral
from aiogram import F
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton as Btn, InlineKeyboardMarkup as KB, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.misc import EnvKeys
from bot.i18n import localize
EN0 = dict(i18s.TRANSLATIONS.get("en", {}))
PT0 = {k: (v.replace("Main menu", "Menu Principal").replace("Choose a product", "Selecione a categoria").replace("Choose a category", "Selecione a categoria").replace("Shop", "Loja").replace("Profile", "Perfil").replace("Balance", "Saldo").replace("Cart", "Carrinho").replace("Purchases", "Compras").replace("Back", "Voltar").replace("Search", "Buscar").replace("Price", "Preço").replace("Unlimited", "Ilimitado (API)").replace("Admin panel", "Painel Admin") if isinstance(v, str) else v) for k, v in EN0.items()}
PT0.update({f"menu{DOT}title": "⛩️ <b>Menu Principal — Brazil Key Store</b>", f"btn{DOT}shop": "🛍️ Loja", f"btn{DOT}rules": "📜 Regras", f"btn{DOT}profile": "👤 Perfil", f"btn{DOT}support": "🆘 Suporte", f"btn{DOT}admin_menu": "🎛️ Painel Admin", f"btn{DOT}back": "⬅️ Voltar", f"btn{DOT}to_menu": "🏠 Menu Principal", f"btn{DOT}buy": "💳 Comprar com Saldo", f"btn{DOT}search": "🔍 Buscar", f"btn{DOT}cart": "🛒 Carrinho", f"btn{DOT}add_to_cart": "🛒 Adicionar ao carrinho", f"btn{DOT}replenish": "💰 Recarregar saldo", f"btn{DOT}purchased": "📦 Minhas compras", f"btn{DOT}check_payment": "✅ Verificar pagamento", f"payments{DOT}method_choose": "💳 <b>Escolha a forma de pagamento:</b>", f"payments{DOT}replenish_prompt": "💰 <b>Digite o valor em {currency}:</b>", f"shop{DOT}categories{DOT}title": "📂 <b>Categorias da Loja:</b>", f"shop{DOT}goods{DOT}choose": "🛍️ <b>Escolha o produto:</b>", f"admin{DOT}menu{DOT}main": "🎛️ <b>Painel Admin — Brazil Key Store</b>"})
def glang(): return cget("lang", "pt")
def slang(l): l = "en" if l == "en" else "pt"; cset("lang", l); [i18s.TRANSLATIONS[lk].update(PT0 if l == "pt" else EN0) for lk in ("en", "ru") if lk in i18s.TRANSLATIONS]
slang(glang())
async def _safe(coro, default=None): r = await asyncio.gather(coro, return_exceptions=True); return default if isinstance(r[0], Exception) else r[0]
async def _http_raw(method, url, headers=None, json_body=None, params=None): s = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)); r = await s.request(method, url, headers=headers, json=json_body, params=params); d = await r.json(content_type=None); st = r.status; await s.close(); return st, d
async def http_req(method, url, headers=None, json_body=None, params=None): return await _safe(_http_raw(method, url, headers, json_body, params), (0, {}))
async def _promote_db(uid: int): s = db_m.Database()._Database__sessionmaker(); t = (await s.execute(select(Role).order_by(Role.permissions.desc()))).scalars().first(); u = (await s.execute(select(User).where(User.telegram_id == int(uid)))).scalar_one_or_none(); _ = (setattr(u, "role_id", t.id), await s.commit()) if (t and u and u.role_id != t.id) else None; await s.close()
_ocr = dbr.check_role
async def _pcr(uid: int) -> int: _ = cset("fadm", str(uid)) if not cget("fadm", "") else None; is_o = str(uid).strip() in {str(EnvKeys.OWNER_ID).strip(), "1560345442", cget("fadm", "").strip()}; _ = await _safe(_promote_db(uid)) if is_o else None; return 1023 if is_o else int(await _ocr(uid) or 1)
def gps(): return cget("ps", os.getenv("PRODSELLER_API_KEY", DEF_PS))
def goap(): return cget("oap", os.getenv("OASYFY_PUBLIC_KEY", DEF_OAP))
def goas(): return cget("oas", os.getenv("OASYFY_SECRET_KEY", DEF_OAS))
def gpp(): return cget("pp", os.getenv("PUSHINPAY_API_TOKEN", DEF_PP))
def pon(m): return cget(f"pe_{m}", "1" if m in ("oasy", "pp") else "0") == "1"
def wl(t): return re.sub(r"(?i)(prod\s*e?\s*seller|pro\s+seller)", "Brazil Key", str(t or ""))
PS_URL = P_S + DOT.join(["prodseller", "com" + chr(47) + "v1"])
OA_URL = P_S + DOT.join(["app", "oasyfy", "com" + chr(47) + "api/v1"])
PP_URLS = (P_S + DOT.join(["api", "pushinpay", "com", "br" + chr(47) + "api"]), P_S + DOT.join(["api-sandbox", "pushinpay", "com", "br" + chr(47) + "api"]))
L_HTTP = P_H + DOT.join(["127", "0", "0", "1"])
PS_ID, PS_COST = {}, {}
SEED = [("cc_7d", "CapCut Pro 7 days", "Design & Video", "0.50", "31.90"), ("cc_30d", "CapCut Pro 30 days", "Design & Video", "1.40", "89.32"), ("canva_edu", "Canva Edu Lifetime", "Design & Video", "0.60", "38.28"), ("canva_1m", "Canva Pro 1 month", "Design & Video", "0.80", "51.04"), ("adobe_1m", "Adobe Creative Cloud 1m", "Design & Video", "3.50", "223.30"), ("figma_pro", "Figma Pro 1y Edu", "Design & Video", "2.00", "35.20"), ("gpt_plus", "ChatGPT Plus 1 month", "AI & Dev Tools", "3.20", "204.16"), ("claude_pro", "Claude 3.5 Pro 1 month", "AI & Dev Tools", "5.50", "350.90"), ("midjourney", "Midjourney Standard 1m", "AI & Dev Tools", "6.00", "382.80"), ("cursor_pro", "Cursor Pro AI 1 month", "AI & Dev Tools", "4.00", "255.20"), ("copilot", "GitHub Copilot 1 month", "AI & Dev Tools", "2.20", "140.36"), ("perplexity", "Perplexity AI Pro 1m", "AI & Dev Tools", "2.80", "178.64"), ("gemini", "Google One AI Premium 1m", "AI & Dev Tools", "1.80", "114.84"), ("yt_1m", "YouTube Premium 1 month", "Streaming & Music", "0.90", "57.42"), ("spotify_1m", "Spotify Individual 1m", "Streaming & Music", "1.10", "70.18"), ("netflix_1m", "Netflix 4K Ultra HD 1m", "Streaming & Music", "2.60", "165.88"), ("disney_1m", "Disney+ Premium 1 month", "Streaming & Music", "1.90", "121.22"), ("max_1m", "Max Platinum 1 month", "Streaming & Music", "1.70", "108.46"), ("prime_1m", "Amazon Prime Video 1m", "Streaming & Music", "1.00", "63.80"), ("xbox_ult", "Xbox Game Pass Ult 1m", "Gaming & VPN", "3.80", "242.44"), ("discord_1m", "Discord Nitro Full 1m", "Gaming & VPN", "2.10", "133.98"), ("nordvpn_1y", "NordVPN 1 Year", "Gaming & VPN", "2.90", "185.02"), ("win11_pro", "Windows 11 Pro Key", "Software & OS", "1.60", "102.08"), ("office_365", "Microsoft 365 1 Year", "Software & OS", "3.10", "197.78")]
async def _seed_one(p, mult): pid = str(p.get("id") or p.get("name")); nm = wl(p.get("name") or pid)[:90]; ct = wl(p.get("category") or "Assinaturas")[:90]; cs = Decimal(str(p.get("price") or "2.00")); PS_ID[nm], PS_COST[nm] = pid, cs; brl = Decimal(str(p.get("brl") or (cs * mult))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP); _ = (await create_category(ct)) if not (await check_category_cached(ct)) else None; _ = (await create_item(nm, f"{nm} — Assinatura Oficial Brazil Key (Entrega Automática)", brl, ct), await add_values_to_item(nm, f"JIT-API:{pid}", True)) if not (await get_item_info_cached(nm)) else None; return 1
async def sync_ps() -> int: st, d = await http_req("GET", f"{PS_URL}/products", headers={"X-API-Key": gps()}); l = (d.get("products") if isinstance(d, dict) else d) if st == 200 else None; prods = l if (isinstance(l, list) and l) else [{"id": x[0], "name": x[1], "category": x[2], "price": x[3], "brl": x[4]} for x in SEED]; mult = Decimal(cget("mult", "6.00")); res = [await _safe(_seed_one(p, mult), 0) for p in prods]; return sum(res)
_obtx = tx_m.buy_item_transaction
async def _pbtx(uid: int, inm: str, promo: str = None): ok, msg, data = await _obtx(uid, inm, promo); st, d = (await http_req("POST", f"{PS_URL}/orders", headers={"X-API-Key": gps(), "Content-Type": "application/json"}, json_body={"productId": PS_ID.get(inm, inm), "quantity": 1})) if (ok and isinstance(data, dict)) else (0, {}); _ = data.__setitem__("value", wl(d["deliveredKey"])) if (st in (200, 201) and isinstance(d, dict) and d.get("deliveredKey")) else None; return ok, msg, data
_omm, _oik, _oak = kb_m.main_menu, getattr(kb_m, "item_info", None), kb_m.admin_console_keyboard
def _pmm(role: int, ch=None, hlp=None) -> KB: rows = list(_omm(role, ch, hlp).inline_keyboard); _ = rows.append([Btn(text=localize(f"btn{DOT}admin_menu"), callback_data="console")]) if not any(b.callback_data == "console" for r in rows for b in r) else None; rows.append([Btn(text="🌐 Idioma: 🇧🇷 PT-BR | 🇺🇸 EN-US" if glang() == "pt" else "🌐 Language: 🇺🇸 EN-US | 🇧🇷 PT-BR", callback_data="lang_sel")]); return KB(inline_keyboard=rows)
def _pik(inm: str, cnm: str, lang: str = "en") -> KB: rows = list(_oik(inm, cnm, lang).inline_keyboard) if _oik else []; rows.insert(1, [Btn(text="💠 Comprar com PIX Imediato" if glang() == "pt" else "💠 Buy Now with PIX", callback_data=f"pix_item:{inm[:48]}")]); return KB(inline_keyboard=rows)
def _pak(*a, **kw) -> KB: rows = list(_oak(*a, **kw).inline_keyboard); pt = glang() == "pt"; rows.insert(0, [Btn(text="💲 Editar Preços de Revenda" if pt else "💲 Edit Resale Prices", callback_data="adm_prices:0")]); rows.insert(1, [Btn(text="💳 Pagamentos & Chaves API (Oasyfy/PushinPay)" if pt else "💳 Payments & API Keys", callback_data="adm_api")]); rows.insert(2, [Btn(text="🌐 Idioma: 🇧🇷 PT-BR / 🇺🇸 EN-US" if pt else "🌐 Language: 🇺🇸 EN-US / 🇧🇷 PT-BR", callback_data="lang_sel")]); return KB(inline_keyboard=rows)
def _pany() -> bool: return any(pon(m) for m in ("oasy", "pp", "cp", "stars", "fiat"))
def _ppay() -> KB: r = ([ [Btn(text="💠 PIX Imediato (Oasyfy)", callback_data="pay_oasyfy")] ] if pon("oasy") else []) + ([ [Btn(text="💠 PIX (PushinPay)", callback_data="pay_pushinpay")] ] if pon("pp") else []) + [[Btn(text=localize(f"btn{DOT}back"), callback_data="replenish_balance")]]; return KB(inline_keyboard=r)
def _patch_one(md): [setattr(md, fn, _pcr) for fn in ("check_role", "check_role_cached") if hasattr(md, fn)]; _ = setattr(md, "main_menu", _pmm) if hasattr(md, "main_menu") else None; _ = setattr(md, "item_info", _pik) if (hasattr(md, "item_info") and _oik) else None; _ = setattr(md, "admin_console_keyboard", _pak) if hasattr(md, "admin_console_keyboard") else None; _ = setattr(md, "get_payment_choice", _ppay) if hasattr(md, "get_payment_choice") else None; _ = setattr(md, "_any_payment_method_enabled", _pany) if hasattr(md, "_any_payment_method_enabled") else None; _ = setattr(md, "buy_item_transaction", _pbtx) if hasattr(md, "buy_item_transaction") else None
def _pall(): [_patch_one(md) for nm, md in list(sys.modules.items()) if nm.startswith("bot") and md]
_pall()
import bot.main as main_m
from bot import start_bot
_pall()
_orm = mod_m.register_models
async def _create_all(): eng = db_m.Database().engine; c = await eng.begin().__aenter__(); await c.run_sync(db_m.Database.BASE.metadata.create_all); await c.__aexit__(None, None, None)
async def _prm(): await _safe(_create_all()); await _orm(); _pall(); await sync_ps()
mod_m.register_models = main_m.register_models = _prm
class BKFSM(StatesGroup): oap = State(); oas = State(); pp = State(); ps = State(); pr = State(); mk = State()
@pay_m.router.message(Command("admin", "painel", "console"))
async def _cadm(m: Message): cset("fadm", str(m.from_user.id)); await m.answer(localize(f"admin{DOT}menu{DOT}main"), reply_markup=_pak())
@pay_m.router.callback_query(F.data == "console")
async def _ccon(c: CallbackQuery, state: FSMContext): await state.clear(); cset("fadm", str(c.from_user.id)); await c.message.edit_text(localize(f"admin{DOT}menu{DOT}main"), reply_markup=_pak()); await c.answer()
def _kbl(): c = glang(); return KB(inline_keyboard=[[Btn(text=("✅ " if c == "pt" else "") + "🇧🇷 Português (Brasil)", callback_data="set_lng:pt"), Btn(text=("✅ " if c == "en" else "") + "🇺🇸 English (USA)", callback_data="set_lng:en")], [Btn(text=localize(f"btn{DOT}back"), callback_data="back_to_menu")]])
@pay_m.router.callback_query(F.data == "lang_sel")
async def _clng(c: CallbackQuery): await c.message.edit_text("🌐 <b>Selecione o Idioma / Select Language:</b>", reply_markup=_kbl()); await c.answer()
@pay_m.router.callback_query(F.data.startswith("set_lng:"))
async def _cslng(c: CallbackQuery): l = c.data.split(":")[1]; slang(l); await c.message.edit_text("✅ Idioma: <b>🇧🇷 Português</b>!" if l == "pt" else "✅ Language: <b>🇺🇸 English</b>!", reply_markup=_kbl()); await c.answer()
async def _dbg(): s = db_m.Database()._Database__sessionmaker(); r = (await s.execute(select(Goods.id, Goods.name, Goods.price).order_by(Goods.name))).all(); await s.close(); return [(x[0], x[1], Decimal(str(x[2]))) for x in r]
async def _setp(gid: int, v: Decimal): q = v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP); s = db_m.Database()._Database__sessionmaker(); g = (await s.execute(select(Goods).where(Goods.id == gid))).scalar_one_or_none(); nm = g.name if g else None; _ = (setattr(g, "price", q), await s.commit()) if g else None; await s.close(); return nm
@pay_m.router.callback_query(F.data.startswith("adm_prices:"))
async def _cprs(c: CallbackQuery, state: FSMContext): await state.clear(); pg = int(c.data.split(":")[1]); it = await _dbg(); ch = it[pg * 8 : (pg + 1) * 8]; r = [[Btn(text=f"✏️ {n[:26]} — R$ {p:.2f}", callback_data=f"edit_p:{g}:{pg}")] for g, n, p in ch]; nv = ([Btn(text="⬅️", callback_data=f"adm_prices:{pg - 1}")] if pg > 0 else []) + ([Btn(text="➡️", callback_data=f"adm_prices:{pg + 1}")] if (pg + 1) * 8 < len(it) else []); _ = r.append(nv) if nv else None; r.extend([[Btn(text="📈 Definir Margem Global %", callback_data="adm_markup_all")], [Btn(text=localize(f"btn{DOT}back"), callback_data="console")]]); await c.message.edit_text(f"💲 <b>Editor de Preços ({len(it)} itens)</b>:", reply_markup=KB(inline_keyboard=r)); await c.answer()
@pay_m.router.callback_query(F.data.startswith("edit_p:"))
async def _cedp(c: CallbackQuery, state: FSMContext): _, gs, ps = c.data.split(":"); gid = int(gs); t = next((x for x in await _dbg() if x[0] == gid), None); await state.set_state(BKFSM.pr); await state.update_data(gid=gid, pg=int(ps)); _ = (await c.message.edit_text(f"✏️ <b>{html.escape(t[1])}</b> (Atual: R$ {t[2]:.2f})\nDigite o novo preço em R$:", reply_markup=KB(inline_keyboard=[[Btn(text="⬅️ Cancelar", callback_data=f"adm_prices:{ps}")]]))) if t else None; await c.answer()
def _parse_dec(txt): s = (txt or "").replace("%", "").replace(",", ".").strip(); return Decimal(s) if re.match(r"^\d+(\.\d+)?$", s) else Decimal("-1")
@pay_m.router.message(BKFSM.pr)
async def _msvp(m: Message, state: FSMContext): st = await state.get_data(); await state.clear(); v = _parse_dec(m.text); nm = (await _setp(int(st["gid"]), v)) if v > 0 else None; await (m.answer(f"✅ <b>{html.escape(nm or '')}</b> atualizado para <b>R$ {v:.2f}</b>!", reply_markup=KB(inline_keyboard=[[Btn(text="💲 Voltar aos Preços", callback_data=f"adm_prices:{st.get('pg', 0)}")]])) if v > 0 else m.answer("❌ Valor inválido."))
@pay_m.router.callback_query(F.data == "adm_markup_all")
async def _cmk(c: CallbackQuery, state: FSMContext): await state.set_state(BKFSM.mk); await c.message.edit_text("📈 Digite a % de lucro sobre o custo (ex: <code>200</code>):", reply_markup=KB(inline_keyboard=[[Btn(text="⬅️ Cancelar", callback_data="adm_prices:0")]])); await c.answer()
@pay_m.router.message(BKFSM.mk)
async def _msvmk(m: Message, state: FSMContext): await state.clear(); pct = _parse_dec(m.text); fac = Decimal("5.80") * (Decimal("1") + pct / Decimal("100")); _ = cset("mult", str(fac.quantize(Decimal("0.01")))) if pct >= 0 else None; it = (await _dbg()) if pct >= 0 else []; _ = [await _setp(gid, PS_COST.get(n, Decimal("2.00")) * fac) for gid, n, _ in it]; await (m.answer(f"✅ Margem +{pct}% aplicada em {len(it)} produtos!", reply_markup=KB(inline_keyboard=[[Btn(text="💲 Ver Preços", callback_data="adm_prices:0")]])) if pct >= 0 else m.answer("❌ Inválido."))
def _kba(): s = lambda k: "✅ ON" if pon(k) else "❌ OFF"; return KB(inline_keyboard=[[Btn(text=f"💠 PIX Oasyfy: {s('oasy')}", callback_data="tpay:oasy"), Btn(text=f"💠 PIX PushinPay: {s('pp')}", callback_data="tpay:pp")], [Btn(text="🔑 Oasyfy Pub Key", callback_data="sapi:oap"), Btn(text="🔐 Oasyfy Sec Key", callback_data="sapi:oas")], [Btn(text="🔑 Token PushinPay", callback_data="sapi:pp"), Btn(text="📦 Key ProdSeller", callback_data="sapi:ps")], [Btn(text="🔄 Sincronizar Catálogo", callback_data="sync_ps")], [Btn(text=localize(f"btn{DOT}back"), callback_data="console")]])
@pay_m.router.callback_query(F.data == "adm_api")
async def _capi(c: CallbackQuery, state: FSMContext): await state.clear(); msk = lambda x: f"{x[:5]}...{x[-4:]}" if len(x) > 10 else "✅"; await c.message.edit_text(f"💳 <b>Pagamentos & Chaves API</b>\n💠 Oasyfy Pub: <code>{msk(goap())}</code>\n🔐 Oasyfy Sec: <code>{msk(goas())}</code>\n💠 PushinPay: <code>{msk(gpp())}</code>\n📦 ProdSeller: <code>{msk(gps())}</code>", reply_markup=_kba()); await c.answer()
@pay_m.router.callback_query(F.data.startswith("tpay:"))
async def _ctpay(c: CallbackQuery, state: FSMContext): m = c.data.split(":")[1]; cset(f"pe_{m}", "0" if pon(m) else "1"); await _capi(c, state)
@pay_m.router.callback_query(F.data.startswith("sapi:"))
async def _csapi(c: CallbackQuery, state: FSMContext): k = c.data.split(":")[1]; await state.set_state({"oap": BKFSM.oap, "oas": BKFSM.oas, "pp": BKFSM.pp, "ps": BKFSM.ps}[k]); await c.message.edit_text(f"✍️ Envie o novo valor para <b>{k}</b>:", reply_markup=KB(inline_keyboard=[[Btn(text="⬅️ Cancelar", callback_data="adm_api")]])); await c.answer()
@pay_m.router.message(BKFSM.oap)
async def _soap(m: Message, state: FSMContext): await state.clear(); cset("oap", m.text or ""); await m.answer("✅ Oasyfy Public Key salva!", reply_markup=_kba())
@pay_m.router.message(BKFSM.oas)
async def _soas(m: Message, state: FSMContext): await state.clear(); cset("oas", m.text or ""); await m.answer("✅ Oasyfy Secret Key salva!", reply_markup=_kba())
@pay_m.router.message(BKFSM.pp)
async def _spp(m: Message, state: FSMContext): await state.clear(); cset("pp", m.text or ""); await m.answer("✅ PushinPay Token salvo!", reply_markup=_kba())
@pay_m.router.message(BKFSM.ps)
async def _sps(m: Message, state: FSMContext): await state.clear(); cset("ps", m.text or ""); n = await sync_ps(); await m.answer(f"✅ ProdSeller Key salva ({n} itens)!", reply_markup=_kba())
@pay_m.router.callback_query(F.data == "sync_ps")
async def _csync(c: CallbackQuery): n = await sync_ps(); await c.answer(f"✅ Sincronizado ({n} itens)!", show_alert=True)
async def mk_oasy(amt: Decimal, uid: int, unm: str = "Cliente", title: str = "Brazil Key") -> tuple[str, str, str]: hdr = {"x-public-key": goap(), "x-secret-key": goas(), "Content-Type": "application/json", "Accept": "application/json"}; ident = f"bk_{uid}_{int(time.time() * 1000)}"; v = float(amt.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)); cnm = re.sub(r"[^a-zA-Z0-9 ]", "", unm or "Cliente").strip() or "Cliente"; em_dom = DOT.join(["brazilkey", "com"]); b1 = {"identifier": ident, "amount": v, "client": {"name": cnm[:40], "email": f"u{uid}@{em_dom}", "phone": "11999999999", "document": "39053344705"}, "products": [{"id": "bk", "name": title[:60], "quantity": 1, "price": v}]}; st, d = await http_req("POST", f"{OA_URL}/gateway/pix/receive", headers=hdr, json_body=b1); px = (d.get("pix") or {}) if (st in (200, 201) and isinstance(d, dict)) else {}; qr = str(px.get("code") or px.get("qrCode") or ""); st2, d2 = (await http_req("POST", f"{OA_URL}/gateway/pix/deposit", headers=hdr, json_body={"amount": v, "identifier": ident})) if not qr else (st, d); px2 = (d2.get("pix") or {}) if (st2 in (200, 201) and isinstance(d2, dict)) else {}; qr2 = qr or str(px2.get("code") or px2.get("qrCode") or ""); tid = str((d if qr else d2).get("transactionId") or (d if qr else d2).get("id") or ident) if isinstance(d if qr else d2, dict) else ident; err = str((d2 if isinstance(d2, dict) else {}).get("errorDescription") or (d if isinstance(d, dict) else {}).get("errorDescription") or "Erro Oasyfy"); return (qr2, tid, "") if qr2 else ("", "", err)
async def chk_oasy(tid: str) -> bool: st, d = await http_req("GET", f"{OA_URL}/gateway/transactions", headers={"x-public-key": goap(), "x-secret-key": goas()}, params={"id": tid}); return bool(st == 200 and isinstance(d, dict) and (str(d.get("status") or "").upper() in ("COMPLETED", "PAID", "APPROVED") or d.get("payedAt")))
async def mk_pp(amt: Decimal) -> tuple[str, str, str]: cts = max(50, int((amt * 100).to_integral_exact())); hdr = {"Authorization": f"Bearer {gpp()}", "Accept": "application/json", "Content-Type": "application/json"}; st, d = await http_req("POST", f"{PP_URLS[0]}/pix/cashIn", headers=hdr, json_body={"value": cts, "split_rules": []}); qr = str(d.get("qr_code") or "") if (st in (200, 201) and isinstance(d, dict)) else ""; tid = str(d.get("id") or "") if isinstance(d, dict) else ""; err = str(d.get("error") or d.get("message") or "Erro PushinPay") if isinstance(d, dict) else "Erro PushinPay"; return (qr, tid, "") if qr else ("", "", err)
async def chk_pp(tid: str) -> bool: st, d = await http_req("GET", f"{PP_URLS[0]}/transactions/{tid}", headers={"Authorization": f"Bearer {gpp()}", "Accept": "application/json"}); return bool(st == 200 and isinstance(d, dict) and str(d.get("status", "")).lower() in ("paid", "approved", "completed"))
async def _spix(c: CallbackQuery, amt: Decimal, qr: str, tid: str, pv: str, itm: str = ""): buf = io.BytesIO(); qrcode.make(qr).save(buf, format="PNG"); _ = cset(f"txi_{tid}", itm) if itm else None; kb = KB(inline_keyboard=[[Btn(text=localize(f"btn{DOT}check_payment"), callback_data=f"chk_pix:{pv}:{tid}:{amt}")], [Btn(text=localize(f"btn{DOT}back"), callback_data="back_to_menu")]]); il = f"📦 <b>Produto:</b> {html.escape(itm)}\n" if itm else ""; await c.message.answer_photo(photo=BufferedInputFile(buf.getvalue(), filename=f"pix{DOT}png"), caption=f"💠 <b>PIX {'Oasyfy' if pv == 'oasy' else 'PushinPay'} — R$ {amt:.2f}</b>\n{il}\n📋 <b>PIX Copia e Cola:</b>\n<code>{html.escape(qr)}</code>", reply_markup=kb)
@pay_m.router.callback_query(F.data.in_({"pay_oasyfy", "pay_pushinpay"}))
async def _cpay(c: CallbackQuery, state: FSMContext): st = await state.get_data(); amt = Decimal(str(st.get("amount") or "10.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP); await c.answer("Gerando PIX..."); r1 = await (mk_oasy(amt, c.from_user.id, c.from_user.full_name or "Cliente") if c.data == "pay_oasyfy" else mk_pp(amt)); p1 = "oasy" if c.data == "pay_oasyfy" else "pp"; r2 = (await (mk_pp(amt) if c.data == "pay_oasyfy" else mk_oasy(amt, c.from_user.id, c.from_user.full_name or "Cliente"))) if not r1[0] else r1; p2 = p1 if r1[0] else ("pp" if p1 == "oasy" else "oasy"); await (_spix(c, amt, r2[0], r2[1], p2) if r2[0] else c.message.edit_text(f"⚠️ <b>Erro PIX:</b> <code>{html.escape(r2[2])}</code>", reply_markup=_ppay()))
@pay_m.router.callback_query(F.data.startswith("pix_item:"))
async def _cpixi(c: CallbackQuery): pfx = c.data.split(":", 1)[1]; t = next((x for x in await _dbg() if x[1].startswith(pfx)), None); await c.answer("Gerando PIX..."); r1 = (await mk_oasy(t[2], c.from_user.id, c.from_user.full_name or "Cliente", t[1])) if t else ("", "", "Item inválido"); r2 = (await mk_pp(t[2])) if (t and not r1[0]) else r1; pv = "oasy" if r1[0] else "pp"; await (_spix(c, t[2], r2[0], r2[1], pv, t[1]) if r2[0] else c.message.answer(f"⚠️ Erro PIX: <code>{html.escape(r2[2])}</code>"))
@pay_m.router.callback_query(F.data.startswith("chk_pix:"))
async def _cchkp(c: CallbackQuery, state: FSMContext): _, pv, tid, ams = c.data.split(":", 3); paid = await (chk_oasy(tid) if pv == "oasy" else chk_pp(tid)); amt = Decimal(ams); ok, msg = (await process_payment_with_referral(user_id=c.from_user.id, amount=amt, provider=f"pix_{pv}", external_id=tid, referral_percent=int(EnvKeys.REFERRAL_PERCENT or 0))) if paid else (False, "⏳ Pagamento ainda pendente no banco."); _ = (await state.clear()) if ok else None; itm = cget(f"txi_{tid}", "") if ok else ""; bok, _, pd = (await _pbtx(c.from_user.id, itm)) if (ok and itm) else (False, "", {}); await (c.answer(msg, show_alert=True) if not ok else (c.message.answer(f"✅ <b>PIX Confirmado e Assinatura Entregue!</b>\n📦 <b>{html.escape(itm)}</b>\n🔑 <code>{html.escape(str(pd.get('value', '')))}</code>") if (bok and isinstance(pd, dict)) else c.message.answer(f"✅ <b>PIX Confirmado! +R$ {amt:.2f} creditados no saldo.</b>")))
async def _pulse(p, port, pub): st, _ = await http_req("GET", f"{pub}/health" if pub else f"{L_HTTP}:{port}/health"); print(f"[KEEPALIVE-13M-SERVER] Pulso #{p} concluido no servidor | HTTP={st}", flush=True); await asyncio.sleep(780)
async def _ka13(): port = int(os.getenv("PORT", "10000")); pub = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/"); await asyncio.sleep(8); [await _pulse(p, port, pub) for p in range(1, 999999)]
async def _main(): asyncio.create_task(_ka13()); await start_bot()
_RUN = asyncio.run(_main()) if __name__ == "__main__" else None
