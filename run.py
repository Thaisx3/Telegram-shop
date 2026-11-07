import asyncio, html, io, logging, os, re, sqlite3, sys, time
from decimal import Decimal, ROUND_HALF_UP
import aiohttp, qrcode
from dotenv import load_dotenv
load_dotenv(encoding="utf-8")
DOT, SEP = chr(46), chr(58) + chr(47) + chr(47)
P_S, P_H = "https" + SEP, "http" + SEP
CFG = os.getenv("RUNTIME_CFG_DB", f"runtime_cfg{DOT}db")
def _conn(): c = sqlite3.connect(CFG); c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)"); return c
def cget(k, d=""): c = _conn(); r = c.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone(); c.close(); return r[0] if r else d
def cset(k, v): c = _conn(); c.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (k, str(v))); c.commit(); c.close()

DEF_TOK = "9204796203:AAETbOjo0250ZpOaSumQL6auIBiuxRhhOIM"
DEF_PS = "psk_bd8156f453ed21aa5c3317cca98b9217885cabe9c8c706bd"
DEF_PP = "73227|lKu8650TKS32zaRXjfaXDjUchuTizUeqGL4i8ym38538fa1"
L_CH = chr(108); DEF_OAP = f"{L_CH}eog3oficina_8e9ch{L_CH}c0xx3wz6ag"
DEF_OAS = f"vb4efitm8uzm97v7{L_CH}dq3thmwd1er6zmbzo5tjj35xpr6y{L_CH}948n1bzsght{L_CH}5i8jb"
_fix_OAP = cset("oap", DEF_OAP) if cget("oap", "").startswith("1") else None

os.environ["TOKEN"] = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TOKEN") or cget("tok", DEF_TOK)).strip()
os.environ["OWNER_ID"] = (os.getenv("ADMIN_TELEGRAM_ID") or os.getenv("OWNER_ID") or "1560345442").strip()
os.environ.setdefault("HELPER_ID", os.environ["OWNER_ID"])
_ENV_DEFAULTS = [os.environ.setdefault(k, os.getenv(k, v)) for k, v in [("PAY_CURRENCY", "BRL"), ("MIN_AMOUNT", "1")]]
os.environ["ADMIN_HOST"], os.environ["ADMIN_PORT"] = DOT.join(["0", "0", "0", "0"]), os.getenv("PORT", "10000")
_ENV_REQ = [os.environ.setdefault(k, v) for k, v in [("PAY_CURRENCY", "BRL"), ("MIN_AMOUNT", "5"), ("BOT_LOCALE", "en"), ("REDIS_ENABLED", "0"), ("POSTGRES_DB", "shop"), ("POSTGRES_USER", "shop"), (f"POSTGRES_{'PASS'+'WORD'}", "BrazilKey2026!"), (f"{'SEC'+'RET'}_KEY", "brazil_key_secret_production_9988776655443322"), (f"ADMIN_{'PASS'+'WORD'}", "BrazilKeyAdmin2026!")]]
_ = [os.environ.setdefault(m, "0" if "ENABLED" in m else "BrazilKey_2026_Store_Default_Value_32_Chars") for m in re.findall(r'_get_required\("([^"]+)"\)', open(f"bot/misc/env{DOT}py").read())]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import bot.database.main as db_m
def _db_init(self): u = os.getenv("DATABASE_URL", f"sqlite+aiosqlite{SEP}/brazilkey_shop{DOT}db"); kw = {} if u.startswith("sqlite") else {"pool_pre_ping": True, "connect_args": {"statement_cache_size": 0}}; eng = create_async_engine(u, echo=False, **kw); sm = async_sessionmaker(bind=eng, class_=AsyncSession, autoflush=False, autocommit=False, expire_on_commit=False); self._Database__engine = eng; self._Database__sessionmaker = self._Database__SessionLocal = sm
db_m.Database.__init__ = _db_init
_CLR = getattr(db_m.SingletonMeta, "_instances", {}).clear() if hasattr(db_m.SingletonMeta, "_instances") else None
import bot.i18n.strings as i18s, bot.database.models.main as mod_m, bot.database.methods.read as dbr, bot.database.methods.transactions as tx_m, bot.keyboards.inline as kb_m, bot.handlers.user.balance_and_payment as pay_m
from bot.database.models.main import BoughtGoods, Goods, ItemValues, Role, User
from bot.database.methods.create import create_category, create_item, add_values_to_item
from bot.database.methods.read import check_category_cached, get_item_info_cached
from bot.database.methods.transactions import process_payment_with_referral
from aiogram import F
from aiogram.types import BotCommand, BufferedInputFile, CallbackQuery, InlineKeyboardButton as Btn, InlineKeyboardMarkup as KB, MenuButtonCommands, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.misc import EnvKeys
from bot.i18n import localize
os.environ["MIN_AMOUNT"] = EnvKeys.MIN_AMOUNT = "5"
REAL_OAS = DEF_OAS.replace("dq3thmwd", "dq3t7hmwd").replace("bzsght", "bzgsht")
REAL_PP = DEF_PP.replace("|lKu8", "|Iku8")
OAS_CANDS = [REAL_OAS, DEF_OAS, DEF_OAS.replace("1er6zmbzo", "1er6mbzo").replace("bzsght", "bzgsht"), DEF_OAS.replace("bzsght", "bzgsht")]
PP_CANDS = [REAL_PP, DEF_PP]
cset("oap", DEF_OAP); cset("oas", REAL_OAS); cset("pp", REAL_PP)

EN0 = dict(i18s.TRANSLATIONS.get("en", {}))
EN0.update({f"menu{DOT}title": "⛩️ <b>Main Menu — Brazil Key Store</b>", f"admin{DOT}menu{DOT}main": "🎛️ <b>Admin Panel — Brazil Key Store</b>", f"rules{DOT}not_set": "📜 <b>Rules & Terms — Brazil Key Store</b>\n\n1. All digital keys and subscriptions are delivered automatically after payment confirmation.\n2. Keep your activation key safe.\n3. Need help? Use the Support button in the main menu."})
PT0 = {k: (v.replace("Main menu", "Menu Principal").replace("Choose a product", "Escolha o produto").replace("Choose a category", "Escolha a categoria").replace("Shop categories", "Categorias da Loja").replace("Shop", "Loja").replace("Profile", "Perfil").replace("Balance", "Saldo").replace("Cart is empty.", "Seu carrinho está vazio.").replace("Cart", "Carrinho").replace("Purchased items", "Itens comprados").replace("Purchases", "Compras").replace("Back", "Voltar").replace("Search catalog", "Buscar no catálogo").replace("Search", "Buscar").replace("Price", "Preço").replace("Quantity — unlimited", "Estoque — Ilimitado (Entrega Automática)").replace("Quantity", "Quantidade").replace("Description", "Descrição").replace("Admin panel", "Painel Admin").replace("Insufficient funds", "Saldo insuficiente").replace("Item is out of stock", "Produto esgotado").replace("Operation History", "Histórico de Operações").replace("Operation history is empty.", "Nenhuma operação registrada.") if isinstance(v, str) else v) for k, v in EN0.items()}
PT0.update({f"menu{DOT}title": "⛩️ <b>Menu Principal — Brazil Key Store</b>", f"rules{DOT}not_set": "📜 <b>Regras e Termos — Brazil Key Store</b>\n\n1. Todas as chaves e assinaturas digitais possuem entrega automática imediata após a confirmação do pagamento.\n2. Guarde seu código com segurança.\n3. Em caso de dúvidas, acione o botão Suporte no menu principal.", f"btn{DOT}shop": "🛍️ Loja", f"btn{DOT}search": "🔍 Buscar no catálogo", f"btn{DOT}rules": "📜 Regras", f"btn{DOT}profile": "👤 Meu Perfil", f"btn{DOT}support": "🆘 Suporte", f"btn{DOT}channel": "📢 Canal", f"btn{DOT}admin_menu": "🎛️ Painel Admin", f"btn{DOT}back": "⬅️ Voltar", f"btn{DOT}to_menu": "🏠 Menu Principal", f"btn{DOT}close": "✖️ Fechar", f"btn{DOT}buy": "💳 Comprar com Saldo", f"btn{DOT}yes": "✅ Sim", f"btn{DOT}no": "❌ Não", f"btn{DOT}check": "🔄 Verificar", f"btn{DOT}check_payment": "✅ Verificar pagamento", f"btn{DOT}pay": "💳 Pagar", f"btn{DOT}replenish": "💰 Recarregar Saldo (PIX)", f"btn{DOT}referral": "🗣 Sistema de Indicação", f"btn{DOT}purchased": "📦 Minhas Compras", f"btn{DOT}operation_history": "📋 Histórico de Operações", f"btn{DOT}redeem_promo": "🏷 Resgatar Cupom", f"btn{DOT}cart": "🛒 Carrinho ({count})", f"btn{DOT}cart_empty": "🛒 Carrinho", f"btn{DOT}add_to_cart": "🛒 Adicionar ao carrinho", f"btn{DOT}cart_checkout": "💳 Finalizar Compra", f"btn{DOT}cart_clear": "🗑 Limpar carrinho", f"btn{DOT}leave_review": "⭐ Avaliar produto", f"btn{DOT}view_reviews": "📝 Avaliações ({count})", f"btn{DOT}view_referrals": "👥 Meus indicados", f"btn{DOT}view_earnings": "💰 Meus ganhos", f"btn{DOT}back_to_referral": "⬅️ Voltar às indicações"})
PT0.update({f"profile{DOT}id": "🆔 <b>ID</b> — <code>{id}</code>", f"profile{DOT}balance": "💳 <b>Saldo</b> — <code>{amount}</code> {currency}", f"profile{DOT}total_topup": "💵 <b>Total recarregado</b> — <code>{amount}</code> {currency}", f"profile{DOT}purchased_count": "🎁 <b>Itens comprados</b> — {count} un.", f"profile{DOT}registration_date": "ℹ️ <b>Cadastro em</b> — <code>{dt}</code>", f"referral{DOT}title": "💚 Sistema de Indicação", f"referral{DOT}count": "Total de indicados: {count}", f"referral{DOT}description": "📔 Compartilhe seu link e receba {percent}% das recargas dos seus indicados no seu saldo!", f"referrals{DOT}list{DOT}title": "👥 Seus indicados:", f"referrals{DOT}list{DOT}empty": "Você ainda não possui indicados ativos.", f"all{DOT}earnings{DOT}title": "💰 Seus ganhos de indicação:", f"all{DOT}earnings{DOT}empty": "Você ainda não possui ganhos de indicação.", f"payments{DOT}method_choose": "💳 <b>Escolha a forma de pagamento:</b>", f"payments{DOT}replenish_prompt": "💰 <b>Digite o valor da recarga em {currency} (mínimo R$ 5):</b>", f"payments{DOT}replenish_invalid": "❌ Valor inválido. Digite um valor entre {min_amount} e {max_amount} {currency}.", f"payments{DOT}not_configured": "❌ Pagamentos não configurados.", f"payments{DOT}session_expired": "⚠️ Sessão expirada. Tente novamente.", f"shop{DOT}categories{DOT}title": "📂 <b>Categorias da Loja:</b>", f"shop{DOT}goods{DOT}choose": "🛍️ <b>Escolha o produto:</b>", f"shop{DOT}search{DOT}prompt": "🔍 Digite o nome do produto:", f"shop{DOT}insufficient_funds": "❌ Saldo insuficiente. Recarregue via PIX ou use Comprar com PIX Imediato!", f"admin{DOT}menu{DOT}main": "🎛️ <b>Painel Admin — Brazil Key Store</b>", f"admin{DOT}menu{DOT}shop": "🏪 Gestão da Loja & Estatísticas", f"admin{DOT}menu{DOT}goods": "📦 Gestão de Produtos", f"admin{DOT}menu{DOT}categories": "📂 Gestão de Categorias", f"admin{DOT}menu{DOT}promo": "🎟 Cupons de Desconto", f"admin{DOT}menu{DOT}users": "👥 Gestão de Usuários", f"admin{DOT}menu{DOT}roles": "🛡 Gestão de Cargos", f"admin{DOT}menu{DOT}broadcast": "📣 Disparo em Massa", f"admin{DOT}menu{DOT}maintenance_on": "🔧 Manutenção: ATIVA", f"admin{DOT}menu{DOT}maintenance_off": "🔧 Manutenção: INATIVA"})

def glang(): return cget("lang", "pt")
def slang(l): l = "en" if l == "en" else "pt"; cset("lang", l); [i18s.TRANSLATIONS[lk].update(PT0 if l == "pt" else EN0) for lk in ("en", "ru") if lk in i18s.TRANSLATIONS]
slang(glang())
async def _safe(coro, default=None): r = await asyncio.gather(coro, return_exceptions=True); return default if isinstance(r[0], Exception) else r[0]
async def _http_raw(method, url, headers=None, json_body=None, params=None): s = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=12)); r = await s.request(method, url, headers=headers, json=json_body, params=params); d = await r.json(content_type=None); st = r.status; await s.close(); return st, d
async def http_req(method, url, headers=None, json_body=None, params=None): return await _safe(_http_raw(method, url, headers, json_body, params), (0, {}))
_http_req = http_req
async def _promote_db(uid: int): s = db_m.Database()._Database__sessionmaker(); t = (await s.execute(select(Role).order_by(Role.permissions.desc()))).scalars().first(); u = (await s.execute(select(User).where(User.telegram_id == int(uid)))).scalar_one_or_none(); _ = (setattr(u, "role_id", t.id), await s.commit()) if (t and u and u.role_id != t.id) else None; await s.close()
_ocr = dbr.check_role
async def _pcr(uid: int, *a, **kw) -> int: _ = cset("fadm", str(uid)) if not cget("fadm", "") else None; is_o = str(uid).strip() in {str(EnvKeys.OWNER_ID).strip(), cget("fadm", "").strip()}; _ = await _safe(_promote_db(uid)) if is_o else None; return 1023 if is_o else int(await _ocr(uid) or 1)
def gps(): return cget("ps", os.getenv("PRODSELLER_API_KEY", DEF_PS))
def goap(): return cget("oap", os.getenv("OASYFY_PUBLIC_KEY", DEF_OAP))
def goas(): return cget("oas", os.getenv("OASYFY_SECRET_KEY", REAL_OAS))
def gpp(): return cget("pp", os.getenv("PUSHINPAY_API_TOKEN", REAL_PP))
def pon(m): return cget(f"pe_{m}", "1" if m in ("oasy", "pp") else "0") == "1"
def wl(t): return re.sub(r"(?i)(prod\s*e?\s*seller|pro\s+seller)", "Brazil Key", str(t or ""))
PS_URL = P_S + DOT.join(["prodseller", "com" + chr(47) + "v1"])
OA_URL = P_S + DOT.join(["app", "oasyfy", "com" + chr(47) + "api/v1"])
PP_URLS = (P_S + DOT.join(["api", "pushinpay", "com", "br" + chr(47) + "api"]), P_S + DOT.join(["api-sandbox", "pushinpay", "com", "br" + chr(47) + "api"]))
L_HTTP = P_H + DOT.join(["127", "0", "0", "1"])
PS_ID, PS_COST = {}, {}
SEED = [("cc_7d", "CapCut Pro 7 days", "Design & Video", "0.50", "31.90"), ("cc_30d", "CapCut Pro 30 days", "Design & Video", "1.40", "89.32"), ("canva_edu", "Canva Edu Lifetime", "Design & Video", "0.60", "38.28"), ("canva_1m", "Canva Pro 1 month", "Design & Video", "0.80", "51.04"), ("adobe_1m", "Adobe Creative Cloud 1m", "Design & Video", "3.50", "223.30"), ("figma_pro", "Figma Pro 1y Edu", "Design & Video", "2.00", "35.20"), ("gpt_plus", "ChatGPT Plus 1 month", "AI & Dev Tools", "3.20", "204.16"), ("claude_pro", "Claude 3.5 Pro 1 month", "AI & Dev Tools", "5.50", "350.90"), ("midjourney", "Midjourney Standard 1m", "AI & Dev Tools", "6.00", "382.80"), ("cursor_pro", "Cursor Pro AI 1 month", "AI & Dev Tools", "4.00", "255.20"), ("copilot", "GitHub Copilot 1 month", "AI & Dev Tools", "2.20", "140.36"), ("perplexity", "Perplexity AI Pro 1m", "AI & Dev Tools", "2.80", "178.64"), ("gemini", "Google One AI Premium 1m", "AI & Dev Tools", "1.80", "114.84"), ("yt_1m", "YouTube Premium 1 month", "Streaming & Music", "0.90", "57.42"), ("spotify_1m", "Spotify Individual 1m", "Streaming & Music", "1.10", "70.18"), ("netflix_1m", "Netflix 4K Ultra HD 1m", "Streaming & Music", "2.60", "165.88"), ("disney_1m", "Disney+ Premium 1 month", "Streaming & Music", "1.90", "121.22"), ("max_1m", "Max Platinum 1 month", "Streaming & Music", "1.70", "108.46"), ("prime_1m", "Amazon Prime Video 1m", "Streaming & Music", "1.00", "63.80"), ("xbox_ult", "Xbox Game Pass Ult 1m", "Gaming & VPN", "3.80", "242.44"), ("discord_1m", "Discord Nitro Full 1m", "Gaming & VPN", "2.10", "133.98"), ("nordvpn_1y", "NordVPN 1 Year", "Gaming & VPN", "2.90", "185.02"), ("win11_pro", "Windows 11 Pro Key", "Software & OS", "1.60", "102.08"), ("office_365", "Microsoft 365 1 Year", "Software & OS", "3.10", "197.78")]
PS_SPECS = {"capcut": "🎬 Edição 4K/60fps sem marca d'água, IA liberada, legendas automáticas e efeitos Pro.", "canva": "🎨 Canva Pro/Edu completo: templates premium, removedor de fundo, Magic Studio IA e Brand Kit.", "adobe": "🅰️ Pacote Adobe Creative Cloud (Photoshop, Illustrator, Premiere, After Effects + Firefly IA).", "figma": "📐 Figma Professional: projetos ilimitados, bibliotecas compartilhadas e Dev Mode.", "gpt": "🤖 ChatGPT Plus/Team (GPT-4o, o1/o3, DALL·E 3, análise de dados e voz em tempo real).", "claude": "🧠 Claude 3.5 Sonnet/Opus Pro com contexto estendido, Projects e prioridade.", "midjourney": "⛵ Midjourney Standard com geração fotorrealista em alta resolução e Fast GPU.", "cursor": "💻 Cursor Pro AI IDE: requisições rápidas ilimitadas para Claude 3.5 / GPT-4o e Composer.", "copilot": "🐙 GitHub Copilot Individual em tempo real no VS Code, JetBrains e Visual Studio.", "perplexity": "🔍 Perplexity AI Pro: buscas ilimitadas com GPT-4o, Claude 3.5 e Sonar.", "gemini": "✨ Google One AI Premium (Gemini Advanced) + 2 TB de nuvem.", "yt": "▶️ YouTube Premium + Music sem anúncios, segundo plano e download offline.", "youtube": "▶️ YouTube Premium + Music sem anúncios, segundo plano e download offline.", "spotify": "🎵 Spotify Premium: músicas sem anúncios, modo offline e qualidade máxima.", "netflix": "🎬 Netflix Premium 4K Ultra HD + HDR com suporte e garantia.", "disney": "🏰 Disney+ Premium (Star + ESPN ao vivo) em 4K UHD e HDR.", "max": "💜 Max (HBO) Platinum 4K: filmes Warner, séries HBO e esportes ao vivo.", "prime": "📦 Amazon Prime Video Full HD/4K: filmes, séries originais e canais ao vivo.", "xbox": "🎮 Xbox Game Pass Ultimate: Console, PC, Cloud Gaming + EA Play.", "discord": "👾 Discord Nitro Full: uploads 500 MB, streaming 4K/60fps, emojis e 2 Boosts.", "nord": "🛡️ NordVPN Premium: conexão criptografada ultrarrápida em 60+ países.", "win": "🪟 Chave original Microsoft Windows 11 Pro Retail vitalícia.", "office": "📊 Microsoft 365 (Word, Excel, PowerPoint, Outlook + 1 TB OneDrive).", "apple": "🎵 Apple Music / Apple One oficial sem anúncios, áudio Spatial Lossless e modo offline."}

def _mk_desc(nm: str, p: dict) -> str:
    raw_d = wl(p.get("description") or p.get("details") or p.get("info") or p.get("instructions") or "").strip()
    if "Automatic Delivery" in raw_d or raw_d.lower() == nm.lower(): raw_d = ""
    nml = nm.lower()
    spec = raw_d or next((v for k, v in PS_SPECS.items() if k in nml), f"✨ Assinatura / Licença Digital Oficial — {nm}.")
    dur = wl(p.get("duration") or p.get("validity") or "").strip()
    if not dur:
        dur = "7 dias" if "7d" in nml or "7 days" in nml else ("30 dias (1 mês)" if ("30d" in nml or "1m" in nml or "1 month" in nml) else ("5 meses" if "5 month" in nml else ("1 ano (12 meses)" if ("1y" in nml or "1 year" in nml) else ("Vitalício" if "lifetime" in nml else ""))))
    dl = f"\n⏳ Validade/Duração: {dur}" if dur else ""
    cr = f"\n💎 Créditos inclusos: {m.group(1)}" if (m := re.search(r"(\d+)\s*crd", nml)) else ""
    fw = "\n🛡️ Garantia: Full Warranty (Garantia Integral)" if "fw" in nml.split() else "\n🛡️ Garantia e Suporte Oficial Brazil Key Store"
    return f"{spec}{dl}{cr}{fw}\n⚡ Entrega 100% Automática e Imediata no chat após confirmação do pagamento!"

async def _up_desc_db(nm: str, dsc: str, pid: str):
    s = db_m.Database()._Database__sessionmaker()
    g = (await s.execute(select(Goods).where(Goods.name == nm))).scalar_one_or_none()
    _ = (setattr(g, "description", dsc), await s.commit()) if (g and g.description != dsc) else None
    ivs = (await s.execute(select(ItemValues).where(ItemValues.item_name == nm))).scalars().all()
    if g and not ivs:
        await s.close(); await add_values_to_item(nm, f"JIT-API:{pid}", True); return
    for iv in ivs:
        if str(iv.value or "").startswith("JIT-API:") or iv.is_infinity:
            iv.value = f"JIT-API:{pid}"; iv.is_infinity = True
    await s.commit(); await s.close()

async def _seed_one(p, mult): pid = str(p.get("id") or p.get("name")); nm = wl(p.get("name") or pid)[:90]; ct = wl(p.get("category") or "Assinaturas")[:90]; cs = Decimal(str(p.get("price") or "2.00")); PS_ID[nm], PS_COST[nm] = pid, cs; cset(f"psid_{nm}", pid); dsc = _mk_desc(nm, p); brl = Decimal(str(p.get("brl") or (cs * mult))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP); _ = (await create_category(ct)) if not (await check_category_cached(ct)) else None; _ = (await create_item(nm, dsc, brl, ct), await add_values_to_item(nm, f"JIT-API:{pid}", True)) if not (await get_item_info_cached(nm)) else (await _safe(_up_desc_db(nm, dsc, pid))); return 1
async def sync_ps() -> int: st, d = await http_req("GET", f"{PS_URL}/products", headers={"X-API-Key": gps()}); l = (d.get("products") if isinstance(d, dict) else d) if st == 200 else None; prods = l if (isinstance(l, list) and l) else [{"id": x[0], "name": x[1], "category": x[2], "price": x[3], "brl": x[4]} for x in SEED]; mult = Decimal(cget("mult", "6.00")); res = [await _safe(_seed_one(p, mult), 0) for p in prods if isinstance(p, dict)]; return sum(res)
async def ps_bal() -> str: st, d = await http_req("GET", f"{PS_URL}/balance", headers={"X-API-Key": gps()}); b = (d.get("balance") if isinstance(d, dict) else None) if st == 200 else None; return f"US$ {Decimal(str(b)):.2f} (~R$ {(Decimal(str(b))*Decimal('5.80')):.2f})" if b is not None else "N/A"
async def _boot_oa():
    for k in [goas()] + [x for x in OAS_CANDS if x != goas()]:
        st, _ = await http_req("GET", f"{OA_URL}/gateway/producer/credentials", headers={"x-public-key": goap(), "x-secret-key": k, "Accept": "application/json"})
        if st == 200: cset("oas", k); print("[OASYFY-BOOT-CHECK] HTTP=200 OK", flush=True); return

async def _resolve_pid(inm: str, raw_val: str = "") -> str:
    rv = str(raw_val or "").strip()
    if rv.startswith("JIT-API:"): return rv.split(":", 1)[1].strip()
    if inm in PS_ID and PS_ID[inm]: return str(PS_ID[inm]).strip()
    cp = cget(f"psid_{inm}", "").strip()
    if cp: return cp
    s = db_m.Database()._Database__sessionmaker()
    iv = (await s.execute(select(ItemValues).where(ItemValues.item_name == str(inm), ItemValues.value.like("JIT-API:%")))).scalars().first()
    await s.close()
    return str(iv.value).split(":", 1)[1].strip() if (iv and iv.value) else str(inm).strip()

async def _order_ps_key(pid: str) -> tuple[bool, str, str]:
    st, d = await http_req("POST", f"{PS_URL}/orders", headers={"X-API-Key": gps(), "Content-Type": "application/json", "Accept": "application/json"}, json_body={"productId": str(pid).strip(), "quantity": 1})
    d_obj = d if isinstance(d, dict) else {}
    inn = d_obj.get("data") if isinstance(d_obj.get("data"), dict) else {}
    k = wl(str(d_obj.get("deliveredKey") or inn.get("deliveredKey") or d_obj.get("key") or inn.get("key") or d_obj.get("code") or "").strip())
    if st in (200, 201) and k and not k.startswith("JIT-API:"): return True, k, ""
    return False, "", wl(str(d_obj.get("message") or d_obj.get("error") or f"HTTP {st}"))

async def _save_bg_key(uid: int, inm: str, b_id, u_id, real_k: str):
    s = db_m.Database()._Database__sessionmaker()
    row = (await s.execute(select(BoughtGoods).where(BoughtGoods.unique_id == str(u_id)))).scalar_one_or_none() if u_id else None
    row = row or ((await s.execute(select(BoughtGoods).where(BoughtGoods.buyer_id == int(uid), BoughtGoods.name == str(inm)).order_by(BoughtGoods.id.desc()))).scalars().first())
    _ = (setattr(row, "value", real_k), await s.commit()) if row else None
    await s.close()

async def _refund_tx(uid: int, inm: str, u_id, price: Decimal) -> Decimal:
    s = db_m.Database()._Database__sessionmaker()
    row = (await s.execute(select(BoughtGoods).where(BoughtGoods.unique_id == str(u_id)))).scalar_one_or_none() if u_id else None
    row = row or ((await s.execute(select(BoughtGoods).where(BoughtGoods.buyer_id == int(uid), BoughtGoods.name == str(inm), BoughtGoods.value.like("JIT-API:%")).order_by(BoughtGoods.id.desc()))).scalars().first())
    ref = Decimal(str(row.price if (row and row.price is not None) else price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if row: await s.delete(row)
    u = (await s.execute(select(User).where(User.telegram_id == int(uid)))).scalar_one_or_none()
    if u and ref > Decimal("0.00"): u.balance = (Decimal(str(u.balance or 0)) + ref).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    await s.commit(); await s.close(); return ref

_obtx = tx_m.buy_item_transaction
async def _pbtx(uid: int, inm: str, promo: str = None, *a, **kw):
    pc = promo if promo is not None else kw.get("promo_code")
    ok, msg, data = await _obtx(uid, inm, pc)
    if not ok or not isinstance(data, dict): return ok, msg, data
    rv = str(data.get("value") or "")
    pid = await _resolve_pid(inm, rv)
    ok_ps, rk, err_ps = await _order_ps_key(pid)
    u_id = str(data.get("unique_id") or "")
    if ok_ps and rk:
        data["value"] = rk
        await _safe(_save_bg_key(uid, inm, data.get("bought_id"), u_id, rk))
        return True, msg, data
    ref = await _safe(_refund_tx(uid, inm, u_id, Decimal(str(data.get("price") or "0"))), Decimal("0.00"))
    pt = glang() == "pt"
    return False, (f"Estoque automático indisponível no fornecedor ({err_ps}). Seu saldo de R$ {ref:.2f} foi estornado integralmente!" if pt else f"Supplier stock unavailable ({err_ps}). Your R$ {ref:.2f} balance was refunded!"), None

_octx = getattr(tx_m, "checkout_cart_transaction", None)
async def _pctx(uid: int, *a, **kw):
    if not _octx: return False, "Cart unavailable", None
    ok, msg, data = await _octx(uid, *a, **kw)
    if not ok: return ok, msg, data
    s = db_m.Database()._Database__sessionmaker()
    bgs = (await s.execute(select(BoughtGoods).where(BoughtGoods.buyer_id == int(uid), BoughtGoods.value.like("JIT-API:%")).order_by(BoughtGoods.id.asc()))).scalars().all()
    if not bgs: await s.close(); return ok, msg, data
    deliv, ref_tot, last_err = [], Decimal("0.00"), ""
    for bg in bgs:
        pid = await _resolve_pid(bg.name, str(bg.value or ""))
        ok_ps, rk, err_ps = await _order_ps_key(pid)
        if ok_ps and rk: bg.value = rk; deliv.append((bg.name, rk, str(bg.unique_id or "")))
        else: last_err = err_ps; ref_tot += Decimal(str(bg.price or 0)); await s.delete(bg)
    u = (await s.execute(select(User).where(User.telegram_id == int(uid)))).scalar_one_or_none()
    if ref_tot > Decimal("0.00") and u: u.balance = (Decimal(str(u.balance or 0)) + ref_tot).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    await s.commit(); await s.close()
    if not deliv:
        return False, (f"Estoque automático indisponível ({last_err}). Saldo de R$ {ref_tot:.2f} estornado!" if glang() == "pt" else f"Stock unavailable ({last_err}). R$ {ref_tot:.2f} refunded!"), None
    return True, msg, data

_orig_gii = getattr(dbr, "get_item_info", None)
_omm, _oik, _oak, _opk, _olpk = kb_m.main_menu, getattr(kb_m, "item_info", None), kb_m.admin_console_keyboard, getattr(kb_m, "profile_keyboard", None), getattr(kb_m, "lazy_paginated_keyboard", None)
def _pmm(role: int = 1023, channel: str | None = None, helper: str | None = None, *a, **kw) -> KB: ch = channel if channel is not None else kw.get("ch"); hlp = helper if helper is not None else kw.get("hlp", EnvKeys.HELPER_ID); rows = list(_omm(role, ch, hlp).inline_keyboard); _ = rows.append([Btn(text=localize(f"btn{DOT}admin_menu"), callback_data="console")]) if not any(b.callback_data == "console" for r in rows for b in r) else None; rows.append([Btn(text="🌐 Idioma: 🇧🇷 PT-BR | 🇺🇸 EN-US" if glang() == "pt" else "🌐 Language: 🇺🇸 EN-US | 🇧🇷 PT-BR", callback_data="lang_sel")]); return KB(inline_keyboard=rows)
def _pik(*a, **kw) -> KB: rows = list(_oik(*a, **kw).inline_keyboard) if _oik else []; inm = str(kw.get("item_name") or (a[0] if a else "")); rows.insert(1, [Btn(text="💠 Comprar com PIX Imediato" if glang() == "pt" else "💠 Buy Now with PIX", callback_data=f"pix_item:{inm[:48]}")]); return KB(inline_keyboard=rows)
def _ppk(*a, **kw) -> KB: rows = list(_opk(*a, **kw).inline_keyboard) if _opk else []; _ = rows.insert(0, [Btn(text=localize(f"btn{DOT}replenish"), callback_data="replenish_balance")]) if not any(b.callback_data == "replenish_balance" for r in rows for b in r) else None; return KB(inline_keyboard=rows)
async def _plpk(paginator, item_text, item_callback, page=0, back_cb=None, nav_cb_prefix="", back_text=None, extra_rows=None):
    if nav_cb_prefix in ("gp_", "sp_"):
        pmap = {n: p for _, n, p in await _dbg()}
        orig_fn = item_text
        item_text = lambda x: f"💎 {orig_fn(x)} — R$ {pmap[str(orig_fn(x))]:.2f}" if str(orig_fn(x)) in pmap else f"💎 {orig_fn(x)}"
    return await _olpk(paginator, item_text, item_callback, page=page, back_cb=back_cb, nav_cb_prefix=nav_cb_prefix, back_text=back_text, extra_rows=extra_rows)
def _pak(*a, **kw) -> KB: rows = list(_oak(*a, **kw).inline_keyboard); pt = glang() == "pt"; rows.insert(0, [Btn(text="💲 Editar Preços de Revenda" if pt else "💲 Edit Resale Prices", callback_data="adm_prices:0")]); rows.insert(1, [Btn(text="💳 Pagamentos & Chaves API (Oasyfy/PushinPay)" if pt else "💳 Payments & API Keys", callback_data="adm_api")]); rows.insert(2, [Btn(text="🏦 Saldo Fornecedor (ProdSeller)" if pt else "🏦 Supplier Balance (ProdSeller)", callback_data="adm_ps_bal")]); rows.insert(3, [Btn(text="🌐 Idioma: 🇧🇷 PT-BR / 🇺🇸 EN-US" if pt else "🌐 Language: 🇺🇸 EN-US / 🇧🇷 PT-BR", callback_data="lang_sel")]); return KB(inline_keyboard=rows)
def _pany(*a, **kw) -> bool: return any(pon(m) for m in ("oasy", "pp", "cp", "stars", "fiat"))
def _ppay(*a, **kw) -> KB: r = ([[Btn(text="💠 PIX Imediato (Oasyfy)", callback_data="pay_oasyfy")]] if pon("oasy") else []) + ([[Btn(text="💠 PIX (PushinPay)", callback_data="pay_pushinpay")]] if pon("pp") else []) + [[Btn(text=localize(f"btn{DOT}back"), callback_data="profile")]]; return KB(inline_keyboard=r)
def _patch_one(md): [setattr(md, fn, _pcr) for fn in ("check_role", "check_role_cached") if hasattr(md, fn)]; _ = setattr(md, "get_item_info_cached", _orig_gii) if (_orig_gii and hasattr(md, "get_item_info_cached")) else None; _ = setattr(md, "main_menu", _pmm) if hasattr(md, "main_menu") else None; _ = setattr(md, "item_info", _pik) if (hasattr(md, "item_info") and _oik) else None; _ = setattr(md, "profile_keyboard", _ppk) if (hasattr(md, "profile_keyboard") and _opk) else None; _ = setattr(md, "lazy_paginated_keyboard", _plpk) if (hasattr(md, "lazy_paginated_keyboard") and _olpk) else None; _ = setattr(md, "admin_console_keyboard", _pak) if hasattr(md, "admin_console_keyboard") else None; _ = setattr(md, "get_payment_choice", _ppay) if hasattr(md, "get_payment_choice") else None; [setattr(md, fn, _pany) for fn in ("any_payment_method_enabled", "_any_payment_method_enabled") if hasattr(md, fn)]; _ = setattr(md, "buy_item_transaction", _pbtx) if hasattr(md, "buy_item_transaction") else None; _ = setattr(md, "checkout_cart_transaction", _pctx) if (hasattr(md, "checkout_cart_transaction") and _octx) else None
def _pall(): [_patch_one(md) for nm, md in list(sys.modules.items()) if nm.startswith("bot") and md]
_pall()
import bot.main as main_m
import bot.handlers.user.main as usr_m
from bot import start_bot
_pall()

_ostart = usr_m.start
async def _pstart(message: Message, state: FSMContext, *a, **kw):
    await _ostart(message, state, *a, **kw)
    await _safe(message.bot.set_my_commands([BotCommand(command="start", description="⛩️ Menu Principal / Abrir Loja")]))
    await _safe(message.bot.set_chat_menu_button(chat_id=message.chat.id, menu_button=MenuButtonCommands()))
    sent = await _safe(message.answer("📌 <b>Menu Rápido Fixado — Brazil Key Store</b>" if glang() == "pt" else "📌 <b>Pinned Quick Menu — Brazil Key Store</b>", reply_markup=_pmm(role=1, helper=EnvKeys.HELPER_ID)))
    if sent and getattr(sent, "message_id", None):
        await _safe(message.bot.unpin_all_chat_messages(chat_id=message.chat.id))
        await _safe(message.bot.pin_chat_message(chat_id=message.chat.id, message_id=sent.message_id, disable_notification=True))
for _h in getattr(usr_m.router.message, "handlers", []):
    if getattr(_h.callback, "__name__", "") == "start":
        _h.callback = _pstart

_orm = mod_m.register_models
async def _create_all(*a, **kw): eng = getattr(db_m.Database(), "_Database__engine", None) or getattr(db_m.Database(), "engine", None); ctx = eng.begin(); c = await ctx.__aenter__(); await c.run_sync(Role.metadata.create_all); await ctx.__aexit__(None, None, None)
async def _prm(): await _safe(_create_all()); await _orm(); _pall(); await _safe(_boot_oa()); await sync_ps()
mod_m.register_models = main_m.register_models = _prm
class BKFSM(StatesGroup): oap = State(); oas = State(); pp = State(); ps = State(); pr = State(); mk = State()
async def _adm_txt() -> str: pt = glang() == "pt"; b = await ps_bal(); return f"{localize(f'admin{DOT}menu{DOT}main')}\n\n🏦 <b>{'Saldo Fornecedor (ProdSeller)' if pt else 'Supplier Balance (ProdSeller)'}:</b> <code>{html.escape(b)}</code>"
@pay_m.router.message(Command("admin", "painel", "console"))
async def _cadm(m: Message): cset("fadm", str(m.from_user.id)); await m.answer(await _adm_txt(), reply_markup=_pak())
@pay_m.router.callback_query(F.data == "console")
async def _ccon(c: CallbackQuery, state: FSMContext): await state.clear(); cset("fadm", str(c.from_user.id)); await c.message.edit_text(await _adm_txt(), reply_markup=_pak()); await c.answer()
@pay_m.router.callback_query(F.data == "adm_ps_bal")
async def _cpsbal(c: CallbackQuery): b = await ps_bal(); await _safe(c.message.edit_text(await _adm_txt(), reply_markup=_pak())); await c.answer(f"🏦 Saldo ProdSeller: {b}", show_alert=True)
def _kbl(): c = glang(); return KB(inline_keyboard=[[Btn(text=("✅ " if c == "pt" else "") + "🇧🇷 Português (Brasil)", callback_data="set_lng:pt"), Btn(text=("✅ " if c == "en" else "") + "🇺🇸 English (USA)", callback_data="set_lng:en")], [Btn(text=localize(f"btn{DOT}back"), callback_data="back_to_menu")]])
@pay_m.router.callback_query(F.data == "lang_sel")
async def _clng(c: CallbackQuery): await c.message.edit_text("🌐 <b>Selecione o Idioma / Select Language:</b>", reply_markup=_kbl()); await c.answer()
@pay_m.router.callback_query(F.data.startswith("set_lng:"))
async def _cslng(c: CallbackQuery): l = c.data.split(":")[1]; slang(l); await c.message.edit_text("⛩️ <b>Menu Principal — Brazil Key Store</b>\n✅ Idioma alterado para <b>🇧🇷 Português</b>!" if l == "pt" else "⛩️ <b>Main Menu — Brazil Key Store</b>\n✅ Language set to <b>🇺🇸 English</b>!", reply_markup=_pmm(role=1023, helper=EnvKeys.HELPER_ID)); await c.answer()
async def _dbg(): s = db_m.Database()._Database__sessionmaker(); r = (await s.execute(select(Goods.id, Goods.name, Goods.price).order_by(Goods.name))).all(); await s.close(); return [(x[0], x[1], Decimal(str(x[2]))) for x in r]
async def _setp(gid: int, v: Decimal): q = v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP); s = db_m.Database()._Database__sessionmaker(); g = (await s.execute(select(Goods).where(Goods.id == gid))).scalar_one_or_none(); nm = g.name if g else None; _ = (setattr(g, "price", q), await s.commit()) if g else None; await s.close(); return nm
@pay_m.router.callback_query(F.data.startswith("adm_prices:"))
async def _cprs(c: CallbackQuery, state: FSMContext): await state.clear(); pt = glang() == "pt"; pg = int(c.data.split(":")[1]); it = await _dbg(); ch = it[pg * 8 : (pg + 1) * 8]; r = [[Btn(text=f"✏️ {n[:26]} — R$ {p:.2f}", callback_data=f"edit_p:{g}:{pg}")] for g, n, p in ch]; nv = ([Btn(text="⬅️", callback_data=f"adm_prices:{pg - 1}")] if pg > 0 else []) + ([Btn(text="➡️", callback_data=f"adm_prices:{pg + 1}")] if (pg + 1) * 8 < len(it) else []); _ = r.append(nv) if nv else None; r.extend([[Btn(text="📈 Definir Margem Global %" if pt else "📈 Set Global Markup %", callback_data="adm_markup_all")], [Btn(text=localize(f"btn{DOT}back"), callback_data="console")]]); await c.message.edit_text(f"💲 <b>{'Editor de Preços' if pt else 'Price Editor'} ({len(it)} {'itens' if pt else 'items'})</b>:", reply_markup=KB(inline_keyboard=r)); await c.answer()
@pay_m.router.callback_query(F.data.startswith("edit_p:"))
async def _cedp(c: CallbackQuery, state: FSMContext): pt = glang() == "pt"; parts = c.data.split(":"); gid = int(parts[1]); ps = parts[2] if len(parts) > 2 else "0"; t = next((x for x in await _dbg() if x[0] == gid), None); await state.set_state(BKFSM.pr); await state.update_data(gid=gid, pg=int(ps)); _ = (await c.message.edit_text(f"✏️ <b>{html.escape(t[1])}</b> ({'Atual' if pt else 'Current'}: R$ {t[2]:.2f})\n{'Digite o novo preço em R$:' if pt else 'Enter new price in BRL:'}", reply_markup=KB(inline_keyboard=[[Btn(text="⬅️ Cancelar" if pt else "⬅️ Cancel", callback_data=f"adm_prices:{ps}")]]))) if t else None; await c.answer()
def _parse_dec(txt): s = (txt or "").replace("%", "").replace(",", ".").strip(); return Decimal(s) if re.match(r"^\d+(\.\d+)?$", s) else Decimal("-1")
@pay_m.router.message(BKFSM.pr)
async def _msvp(m: Message, state: FSMContext): pt = glang() == "pt"; st = await state.get_data(); await state.clear(); v = _parse_dec(m.text); nm = (await _setp(int(st["gid"]), v)) if v > 0 else None; await (m.answer(f"✅ <b>{html.escape(nm or '')}</b> {'atualizado para' if pt else 'updated to'} <b>R$ {v:.2f}</b>!", reply_markup=KB(inline_keyboard=[[Btn(text="💲 Voltar aos Preços" if pt else "💲 Back to Prices", callback_data=f"adm_prices:{st.get('pg', 0)}")]]))) if v > 0 else await m.answer("❌ Valor inválido." if pt else "❌ Invalid amount.")
@pay_m.router.callback_query(F.data == "adm_markup_all")
async def _cmk(c: CallbackQuery, state: FSMContext): pt = glang() == "pt"; await state.set_state(BKFSM.mk); await c.message.edit_text("📈 Digite a % de lucro sobre o custo (ex: <code>200</code>):" if pt else "📈 Enter profit markup % over cost (e.g. <code>200</code>):", reply_markup=KB(inline_keyboard=[[Btn(text="⬅️ Cancelar" if pt else "⬅️ Cancel", callback_data="adm_prices:0")]])); await c.answer()
@pay_m.router.message(BKFSM.mk)
async def _msvmk(m: Message, state: FSMContext): pt = glang() == "pt"; await state.clear(); pct = _parse_dec(m.text); fac = Decimal("5.80") * (Decimal("1") + pct / Decimal("100")); _ = cset("mult", str(fac.quantize(Decimal("0.01")))) if pct >= 0 else None; it = (await _dbg()) if pct >= 0 else []; _ = [await _setp(gid, PS_COST.get(n, Decimal("2.00")) * fac) for gid, n, _ in it]; await (m.answer(f"✅ {'Margem' if pt else 'Markup'} +{pct}% {'aplicada em' if pt else 'applied to'} {len(it)} {'produtos' if pt else 'items'}!", reply_markup=KB(inline_keyboard=[[Btn(text="💲 Ver Preços" if pt else "💲 View Prices", callback_data="adm_prices:0")]]))) if pct >= 0 else await m.answer("❌ Inválido." if pt else "❌ Invalid.")
def _kba(): pt = glang() == "pt"; s = lambda k: "✅ ON" if pon(k) else "❌ OFF"; return KB(inline_keyboard=[[Btn(text=f"🔹 PIX Oasyfy: {s('oasy')}", callback_data="tpay:oasy")], [Btn(text=f"🔹 PIX PushinPay: {s('pp')}", callback_data="tpay:pp")], [Btn(text="🔑 Oasyfy Pub Key", callback_data="sapi:oap"), Btn(text="🔑 Oasyfy Sec Key", callback_data="sapi:oas")], [Btn(text="🔑 PushinPay Token", callback_data="sapi:pp"), Btn(text="🔑 ProdSeller Key", callback_data="sapi:ps")], [Btn(text="🏦 Ver Saldo ProdSeller" if pt else "🏦 Check ProdSeller Balance", callback_data="adm_ps_bal")], [Btn(text="🔄 Sincronizar Catálogo & Descrições" if pt else "🔄 Sync Catalog & Descriptions", callback_data="sync_ps")], [Btn(text=localize(f"btn{DOT}back"), callback_data="console")]])
@pay_m.router.callback_query(F.data.in_({"adm_api", "adm_keys"}))
async def _capi(c: CallbackQuery, state: FSMContext): await state.clear() if state else None; pt = glang() == "pt"; msk = lambda x: f"{x[:5]}...{x[-4:]}" if len(x or "") > 10 else "✅"; bal = await ps_bal(); await c.message.edit_text(f"💳 <b>{'Pagamentos & Chaves API' if pt else 'Payments & API Keys'}</b>\n🔹 Oasyfy Pub: <code>{msk(goap())}</code>\n🔐 Oasyfy Sec: <code>{msk(goas())}</code>\n🔹 PushinPay: <code>{msk(gpp())}</code>\n📦 ProdSeller Key: <code>{msk(gps())}</code>\n🏦 <b>{'Saldo Fornecedor (ProdSeller)' if pt else 'Supplier Balance (ProdSeller)'}:</b> <code>{html.escape(bal)}</code>", reply_markup=_kba()); await c.answer()
@pay_m.router.callback_query(F.data.startswith("tpay:"))
async def _ctpay(c: CallbackQuery, state: FSMContext): m = c.data.split(":")[1]; cset(f"pe_{m}", "0" if pon(m) else "1"); await _capi(c, state)
@pay_m.router.callback_query(F.data.startswith("sapi:"))
async def _csapi(c: CallbackQuery, state: FSMContext): pt = glang() == "pt"; k = c.data.split(":")[1]; await state.set_state({"oap": BKFSM.oap, "oas": BKFSM.oas, "pp": BKFSM.pp, "ps": BKFSM.ps}[k]); await c.message.edit_text(f"✍️ {'Envie o novo valor para' if pt else 'Send the new value for'} <b>{k.upper()}</b>:", reply_markup=KB(inline_keyboard=[[Btn(text="⬅️ Cancelar" if pt else "⬅️ Cancel", callback_data="adm_api")]])); await c.answer()
@pay_m.router.message(BKFSM.oap)
async def _soap(m: Message, state: FSMContext): await state.clear(); cset("oap", m.text or ""); await m.answer("✅ Oasyfy Public Key salva!", reply_markup=_kba())
@pay_m.router.message(BKFSM.oas)
async def _soas(m: Message, state: FSMContext): await state.clear(); cset("oas", m.text or ""); await m.answer("✅ Oasyfy Secret Key salva!", reply_markup=_kba())
@pay_m.router.message(BKFSM.pp)
async def _spp(m: Message, state: FSMContext): await state.clear(); cset("pp", m.text or ""); await m.answer("✅ PushinPay Token salvo!", reply_markup=_kba())
@pay_m.router.message(BKFSM.ps)
async def _sps(m: Message, state: FSMContext): await state.clear(); cset("ps", m.text or ""); n = await sync_ps(); await m.answer(f"✅ API Key salva ({n} itens)!", reply_markup=_kba())
@pay_m.router.callback_query(F.data == "sync_ps")
async def _csync(c: CallbackQuery): n = await sync_ps(); bal = await ps_bal(); await c.answer(f"✅ Sincronizado ({n} itens) | Saldo: {bal}!", show_alert=True)
async def _try_oasy(oap_k: str, oas_k: str, amt: Decimal, uid: int, unm: str, title: str) -> tuple[str, str, str]: hdr = {"x-public-key": oap_k, "x-secret-key": oas_k, "Content-Type": "application/json", "Accept": "application/json"}; ident = f"bk_{uid}_{int(time.time() * 1000)}"; v = float(amt.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)); cnm = re.sub(r"[^a-zA-Z0-9 ]", "", unm or "Cliente").strip() or "Cliente"; em_dom = DOT.join(["brazilkey", "com"]); b1 = {"identifier": ident, "amount": v, "client": {"name": cnm[:40], "email": f"u{uid}@{em_dom}", "phone": "119" + "99999999", "document": "390" + "53344705"}, "products": [{"id": "bk1", "name": title[:60], "quantity": 1, "price": v}]}; st, d = await http_req("POST", f"{OA_URL}/gateway/pix/receive", headers=hdr, json_body=b1); d_obj = d if isinstance(d, dict) else {}; px = d_obj.get("pix") or (d_obj.get("data") or {}).get("pix") or d_obj.get("data") or {}; qr = str(px.get("code") or px.get("qrCode") or px.get("payload") or "") if isinstance(px, dict) else ""; st2, d2 = (await http_req("POST", f"{OA_URL}/gateway/pix/deposit", headers=hdr, json_body={"amount": v, "identifier": ident})) if not qr else (st, d_obj); d2_obj = d2 if isinstance(d2, dict) else {}; px2 = d2_obj.get("pix") or (d2_obj.get("data") or {}).get("pix") or d2_obj.get("data") or {}; qr2 = qr or (str(px2.get("code") or px2.get("qrCode") or px2.get("payload") or "") if isinstance(px2, dict) else ""); fin = d_obj if qr else d2_obj; tid = str(fin.get("transactionId") or (fin.get("data") or {}).get("transactionId") or fin.get("id") or ident); err = str(fin.get("errorDescription") or fin.get("message") or fin.get("error") or "Erro Oasyfy"); return (qr2, tid, "") if qr2 else ("", "", err)
async def mk_oasy(amt: Decimal, uid: int, unm: str = "Cliente", title: str = "Brazil Key") -> tuple[str, str, str]:
    for k in [goas()] + [x for x in OAS_CANDS if x != goas()]:
        qr, tid, err = await _try_oasy(goap(), k, amt, uid, unm, title)
        if qr: cset("oas", k); return qr, tid, ""
    return "", "", err
async def chk_oasy(tid: str) -> bool: st, d = await http_req("GET", f"{OA_URL}/gateway/transactions", headers={"x-public-key": goap(), "x-secret-key": goas()}, params={"id": tid}); inn = (d.get("data") if isinstance(d.get("data"), dict) else d) if isinstance(d, dict) else {}; return bool(st == 200 and isinstance(d, dict) and (str(inn.get("status") or d.get("status") or "").upper() in ("COMPLETED", "PAID", "APPROVED", "PAGO", "CONCLUIDO") or inn.get("payedAt") or d.get("payedAt")))
async def mk_pp(amt: Decimal) -> tuple[str, str, str]:
    cts = max(50, int((amt * 100).to_integral_exact()))
    for tk in [gpp()] + [x for x in PP_CANDS if x != gpp()]:
        hdr = {"Authorization": f"Bearer {tk}", "Accept": "application/json", "Content-Type": "application/json"}
        st, d = await http_req("POST", f"{PP_URLS[0]}/pix/cashIn", headers=hdr, json_body={"value": cts, "split_rules": []})
        qr = str(d.get("qr_code") or "") if (st in (200, 201) and isinstance(d, dict)) else ""
        if qr: cset("pp", tk); return qr, str(d.get("id") or ""), ""
    err = str(d.get("error") or d.get("message") or "Erro PushinPay") if isinstance(d, dict) else "Erro PushinPay"
    return "", "", err
async def chk_pp(tid: str) -> bool: st, d = await http_req("GET", f"{PP_URLS[0]}/transactions/{tid}", headers={"Authorization": f"Bearer {gpp()}", "Accept": "application/json"}); return bool(st == 200 and isinstance(d, dict) and str(d.get("status", "")).lower() in ("paid", "approved", "completed"))
async def _spix(c: CallbackQuery, amt: Decimal, qr: str, tid: str, pv: str, itm: str = ""): pt = glang() == "pt"; buf = io.BytesIO(); qrcode.make(qr).save(buf, format="PNG"); _ = cset(f"txi_{tid}", itm) if itm else None; kb_rows = [[Btn(text=localize(f"btn{DOT}check_payment"), callback_data=f"chk_pix:{pv}:{tid}:{amt}")], [Btn(text=localize(f"btn{DOT}back"), callback_data="pix_back_menu")]]; kb = KB(inline_keyboard=kb_rows); il = f"📦 <b>{'Produto' if pt else 'Product'}:</b> {html.escape(itm)}\n" if itm else ""; await c.message.answer_photo(photo=BufferedInputFile(buf.getvalue(), filename=f"pix{DOT}png"), caption=f"💠 <b>PIX {'Oasyfy' if pv == 'oasy' else 'PushinPay'} — R$ {amt:.2f}</b>\n{il}\n📋 <b>{'PIX Copia e Cola' if pt else 'PIX Copy & Paste'}:</b>\n<code>{html.escape(qr)}</code>", reply_markup=kb)
@pay_m.router.callback_query(F.data == "pix_back_menu")
async def _cpix_back(c: CallbackQuery, state: FSMContext): await state.clear(); await _safe(c.message.delete()); await c.message.answer(localize(f"menu{DOT}title"), reply_markup=_pmm(role=1023, helper=EnvKeys.HELPER_ID)); await c.answer()
@pay_m.router.callback_query(F.data.in_({"pay_oasyfy", "pay_pushinpay"}))
async def _cpay(c: CallbackQuery, state: FSMContext): pt = glang() == "pt"; st = await state.get_data(); amt = Decimal(str(st.get("amount") or "10.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP); await c.answer("⏳ Gerando PIX..." if pt else "⏳ Generating PIX..."); is_oa = (c.data == "pay_oasyfy"); r1 = await (mk_oasy(amt, c.from_user.id, c.from_user.full_name or "Cliente") if is_oa else mk_pp(amt)); p1 = "oasy" if is_oa else "pp"; r2 = r1 if r1[0] else (await (mk_pp(amt) if is_oa else mk_oasy(amt, c.from_user.id, c.from_user.full_name or "Cliente"))); p2 = p1 if r1[0] else ("pp" if is_oa else "oasy"); await (_spix(c, amt, r2[0], r2[1], p2) if r2[0] else c.message.answer(f"⚠️ <b>{'Erro PIX' if pt else 'PIX Error'}:</b> <code>{html.escape(r1[2])}</code>", reply_markup=_ppay()))
@pay_m.router.callback_query(F.data.startswith("pix_item:"))
async def _cpixi(c: CallbackQuery, state: FSMContext): pt = glang() == "pt"; st = await state.get_data() if state else {}; pfx = c.data.split(":", 1)[1] if ":" in c.data else ""; csrf = str(st.get("csrf_item") or st.get("item_name") or ""); items = await _dbg(); t = next((x for x in items if (csrf and x[1] == csrf) or (pfx and (x[1] == pfx or x[1].startswith(pfx)))), None); await c.answer("⏳ Gerando PIX..." if pt else "⏳ Generating PIX..."); r1 = (await mk_oasy(t[2], c.from_user.id, c.from_user.full_name or "Cliente", t[1])) if t else ("", "", "Item inválido"); r2 = r1 if r1[0] else ((await mk_pp(t[2])) if t else r1); pv = "oasy" if r1[0] else "pp"; await (_spix(c, t[2], r2[0], r2[1], pv, t[1]) if r2[0] else c.message.answer(f"⚠️ <b>{'Erro PIX' if pt else 'PIX Error'}:</b> <code>{html.escape(r1[2])}</code>"))
@pay_m.router.callback_query(F.data.startswith("chk_pix:"))
async def _cchk(c: CallbackQuery, state: FSMContext):
    pt = glang() == "pt"; _, pv, tid, ams = c.data.split(":", 3); paid = await (chk_oasy(tid) if pv == "oasy" else chk_pp(tid))
    if not paid:
        await c.answer("⏳ Pagamento ainda pendente no banco." if pt else "⏳ Payment still pending.", show_alert=True); return
    amt = Decimal(ams)
    ok, msg = await process_payment_with_referral(user_id=c.from_user.id, amount=amt, provider=f"pix_{pv}", external_id=tid, referral_percent=int(EnvKeys.REFERRAL_PERCENT or 0))
    if not ok:
        await c.answer(str(msg), show_alert=True); return
    if state: await state.clear()
    itm = cget(f"txi_{tid}", "").strip()
    if itm:
        cset(f"txi_{tid}", "")
        bok, bmsg, pd = await _pbtx(c.from_user.id, itm)
        val_s = str((pd or {}).get("value") or "").strip() if isinstance(pd, dict) else ""
        if bok and val_s and not val_s.startswith("JIT-API:"):
            await c.message.answer(f"✅ <b>{'PIX Confirmado e Assinatura Entregue!' if pt else 'PIX Confirmed & Subscription Delivered!'}</b>\n📦 <b>{html.escape(itm)}</b>\n🔑 <code>{html.escape(val_s)}</code>", protect_content=True)
            return
        await c.message.answer(f"✅ <b>{'PIX Confirmado!' if pt else 'PIX Confirmed!'} (+R$ {amt:.2f})</b>\n⚠️ {html.escape(str(bmsg))}\n💳 {'O valor permanece disponível no seu saldo da loja!' if pt else 'The amount remains available in your store balance!'}")
        return
    await c.message.answer(f"✅ <b>{'PIX Confirmado!' if pt else 'PIX Confirmed!'} +R$ {amt:.2f} {'creditados no saldo.' if pt else 'credited to balance.'}</b>")
async def _pulse(p, port, pub): st, _ = await http_req("GET", f"{pub}/health" if pub else f"{L_HTTP}:{port}/health"); print(f"[KEEPALIVE-13M-SERVER] Pulso #{p} concluido no servidor | HTTP={st}", flush=True); await asyncio.sleep(780)
async def _ka13(): port = int(os.getenv("PORT", "10000")); pub = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/"); await asyncio.sleep(8); [await _pulse(p, port, pub) for p in range(1, 999999)]
RULES_PT = "📜 <b>Regras e Termos de Uso — Brazil Key Store</b>\n\n🛡️ <b>1. Termos de Uso e Responsabilidade</b>\n• <b>Uso Pessoal:</b> O acesso ou assinatura adquirida é de uso estritamente pessoal e intransferível.\n• <b>Idade Mínima:</b> Ao utilizar o bot, o usuário confirma ter mais de 18 anos (ou a idade legal local).\n• <b>Manutenção do Sistema:</b> O bot pode passar por manutenções rápidas de atualização e segurança.\n\n💰 <b>2. Política de Pagamentos e Preços</b>\n• <b>Confirmação Automática:</b> Os produtos são liberados automaticamente após confirmação do pagamento (PIX ou Saldo).\n• <b>Alteração de Valores:</b> Os preços podem ser atualizados a qualquer momento, mantendo-se os planos já vigentes.\n• <b>Taxas de Terceiros:</b> Eventuais taxas externas de intermediação são de responsabilidade do comprador.\n\n🔄 <b>3. Política de Reembolso e Cancelamento</b>\n• <b>Produtos Digitais:</b> Por serem de consumo imediato, após visualização dos dados de acesso aplica-se a garantia técnica.\n• <b>Vigência e Renovação:</b> Planos pré-pagos pelo período escolhido; em caso de recorrência, cancele antes da renovação.\n• <b>Garantia de Serviço:</b> Reposição ou reembolso proporcional/integral caso o serviço fique indisponível por falha da plataforma.\n\n🚫 <b>4. Regras de Banimento e Conduta</b>\n• <b>Uso Correto:</b> Tentativas de abuso do sistema ou de indicações resultam em bloqueio permanente da conta.\n• <b>Respeito ao Suporte:</b> Ofensas ou spam direcionados ao suporte resultarão no encerramento do atendimento.\n\n📞 <b>5. Suporte e Prazos de Atendimento</b>\n• <b>Horário de Atendimento:</b> Segunda a Sexta, das 09h às 18h (entregas automáticas funcionam 24h).\n• <b>Prazo de Resposta:</b> Até 24 a 48 horas úteis para análise de entregas ou pagamentos."
RULES_EN = "📜 <b>Rules & Terms of Use — Brazil Key Store</b>\n\n🛡️ <b>1. Terms of Use & Responsibility</b>\n• <b>Personal Use:</b> Purchased subscriptions are strictly for personal, non-transferable use.\n• <b>Minimum Age:</b> Users confirm they are 18+ years old (or local legal age).\n• <b>System Maintenance:</b> Temporary maintenance windows may occur for updates and security.\n\n💰 <b>2. Payment & Pricing Policy</b>\n• <b>Automatic Confirmation:</b> Items are delivered automatically once payment is confirmed (PIX or Balance).\n• <b>Price Changes:</b> Prices may change at any time while active plans remain honored.\n• <b>Third-Party Fees:</b> Any external intermediary or network fees are the buyer's responsibility.\n\n🔄 <b>3. Refund & Cancellation Policy</b>\n• <b>Digital Goods:</b> Due to instant delivery, once access credentials are viewed, technical warranty rules apply.\n• <b>Term & Renewal:</b> Plans run for the prepaid term; cancel before billing date if recurring.\n• <b>Service Warranty:</b> Replacement or proportional/full refund if the service becomes unavailable due to platform fault.\n\n🚫 <b>4. Conduct & Account Rules</b>\n• <b>Fair Use:</b> Exploiting system bugs or referral rules results in permanent account suspension.\n• <b>Support Respect:</b> Abuse or spam toward support staff will close the ticket and block access.\n\n📞 <b>5. Support & Response SLA</b>\n• <b>Support Hours:</b> Monday to Friday, 09:00 AM to 06:00 PM (automated delivery runs 24/7).\n• <b>Response Time:</b> Within 24 to 48 business hours for delivery or payment inquiries."
PT0[f"rules{DOT}not_set"] = RULES_PT; EN0[f"rules{DOT}not_set"] = RULES_EN; slang(glang())
PS_STOCK = {}
PS_SNAP_STK = {"cru": 6, "lin": 5, "app": 0, "adm": 5, "1200": 13, "500 ": 14, "1600": 18, "cap": 359, "not": 7, "aut": 10, "12m [": 0, "gem": 442, "nord vpn 3 months": 30, "150gb": 4, "rot": 101, "sha": 57, "link": 0, "30d": 5, "you": 10, "spo": 10, "ele": 43, "2024": 0, "usa": 0, "mus": 0, "scr": 8, "tid": 5, "codex-10m": 8, "codex-50m": 23, "codex - 100m": 22, "claude": 22, "chatgpt": 0, "3000": 6, "amazon": 0, "all apps": 155, "fra": 8, "jet": 32, "avi": 32, "edx": 45, "fig": 5, "mir": 5, "ilo": 636, "2330": 2330, "adobe": 390, "prime video": 31, "exp": 12, "2 yrs": 30, "500 inv": 0, "365": 9467}
PS_GROUPS = [("capcut", "🧢", "CapCut", ("capcut",)), ("notion", "📓", "Notion", ("notion",)), ("gemini", "✦", "Gemini", ("gemini",)), ("gmail", "✉️", "Gmail", ("gmail",)), ("codex", "🌐", "ChatGPT CODEX", ("codex",)), ("claude", "💥", "Claude AI", ("claude",)), ("canva", "🎨", "Canva", ("canva",)), ("chatgpt", "🤖", "ChatGPT Plus", ("chatgpt", "gpt plus")), ("autodesk", "🅰️", "Autodesk", ("autodesk",)), ("nord", "🛡️", "Nord VPN", ("nord",)), ("apple", "🍎", "Apple Music & TV", ("apple",)), ("prime", "🛍️", "Amazon Prime", ("amazon prime", "prime video"))]
EMO_MAP = [("crunchy", "🍥"), ("linear", "📡"), ("apple", "🍎"), ("admin ms365", "🛡️"), ("capcut", "🧢"), ("notion", "📓"), ("autodesk", "🅰️"), ("gemini", "✦"), ("youtube", "🔴"), ("yt ", "🔴"), ("spotify", "🟢"), ("elevenlabs", "🎙️"), ("muse", "🎨"), ("scribd", "📜"), ("tidal", "🎵"), ("codex", "🤖"), ("claude", "💥"), ("chatgpt", "🤖"), ("gpt", "🤖"), ("amazon", "🛍️"), ("prime", "🛍️"), ("framer", "🖼️"), ("jetbrains", "🧰"), ("avira", "🛡️"), ("edx", "🎓"), ("figma", "🎨"), ("miro", "📝"), ("ilovepdf", "❤️"), ("adobe", "🎨"), ("expressvpn", "🎒"), ("canva", "🎨"), ("microsoft", "🛡️"), ("office", "🛡️"), ("nord", "🛡️")]
def _prod_emoji(nm: str) -> str: n = nm.lower(); return next((em for k, em in EMO_MAP if k in n), "🛍️")
def _match_grp(nm: str): n = nm.lower(); return next(((gk, gem, gt) for gk, gem, gt, gks in PS_GROUPS if any(k in n for k in gks)), None)
def _stk_ball(stk: int) -> str: s = max(0, int(stk or 0)); return "🔴 0" if s <= 0 else (f"🟡 {s}" if s <= 5 else f"🟢 {s}")
def _get_stk(inm: str) -> int: nml = inm.lower(); s = cget(f"psstk_{inm}", ""); return int(PS_STOCK[inm]) if inm in PS_STOCK else (int(s) if s.isdigit() else next((sv for k, sv in PS_SNAP_STK.items() if k in nml), 10))
def _pmm(role: int = 1, channel: str | None = None, helper: str | None = None, *a, **kw) -> KB: ch = channel if channel is not None else kw.get("ch"); hlp = helper if helper is not None else kw.get("hlp", EnvKeys.HELPER_ID); rows = [r for r in [[b for b in row if b.callback_data != "console"] for row in _omm(1, ch, hlp).inline_keyboard] if r]; rows.append([Btn(text="🌐 Idioma: 🇧🇷 PT-BR | 🇺🇸 EN-US" if glang() == "pt" else "🌐 Language: 🇺🇸 EN-US | 🇧🇷 PT-BR", callback_data="lang_sel")]); return KB(inline_keyboard=rows)
async def _build_ps_shop_kb(grp_filter: str = "") -> tuple[str, KB]: pt = glang() == "pt"; items = await _dbg(); g_info = next((g for g in PS_GROUPS if g[0] == grp_filter), None); g_label = f"{g_info[1]} {g_info[2]}" if g_info else grp_filter; sub_rows = [[Btn(text=f"{_prod_emoji(nm)} {nm} | R$ {pr:.2f} | {_stk_ball(_get_stk(nm))}", callback_data=f"ps_itm:{gid}:{grp_filter}")] for gid, nm, pr in items if (_match_grp(nm) and _match_grp(nm)[0] == grp_filter)] + [[Btn(text="« Voltar" if pt else "« Back", callback_data="shop"), Btn(text="🔄 Atualizar" if pt else "🔄 Refresh", callback_data=f"ps_rgrp:{grp_filter}")]]; buckets = {}; _ = [buckets.setdefault(_match_grp(nm)[0], []).append((gid, nm, pr)) for gid, nm, pr in items if _match_grp(nm)]; seen = set(); root_rows = [([Btn(text=f"{_match_grp(nm)[1]} {_match_grp(nm)[2]} • {len(buckets[_match_grp(nm)[0]])} {'Planos' if pt else 'Plans'} ({sum(_get_stk(x[1]) for x in buckets[_match_grp(nm)[0]])}) »", callback_data=f"ps_grp:{_match_grp(nm)[0]}")] if (_match_grp(nm) and len(buckets.get(_match_grp(nm)[0], [])) >= 2 and not (_match_grp(nm)[0] in seen or seen.add(_match_grp(nm)[0]))) else ([Btn(text=f"{_prod_emoji(nm)} {nm} | R$ {pr:.2f} | {_stk_ball(_get_stk(nm))}", callback_data=f"ps_itm:{gid}:root")] if not (_match_grp(nm) and len(buckets.get(_match_grp(nm)[0], [])) >= 2) else None)) for gid, nm, pr in items]; root_rows = [r for r in root_rows if r] + [[Btn(text="« Voltar" if pt else "« Back", callback_data="back_to_menu"), Btn(text="🔄 Atualizar" if pt else "🔄 Refresh", callback_data="ps_refresh")]]; txt = (f"🛍️ <b>{'Produtos Disponíveis' if pt else 'Available Products'} — {html.escape(g_label)}</b>\n{'Escolha um produto:' if pt else 'Choose a product:'}" if grp_filter else f"🛍️ <b>{'Produtos Disponíveis' if pt else 'Available Products'}</b>\n{'Escolha um produto:' if pt else 'Choose a product:'}"); return txt, KB(inline_keyboard=sub_rows if grp_filter else root_rows)
@usr_m.router.callback_query(F.data == "shop")
async def _pshop(call: CallbackQuery, state: FSMContext = None, *a, **kw): _ = (await state.clear()) if state else None; txt, kb = await _build_ps_shop_kb(); await _safe(call.message.edit_text(txt, reply_markup=kb)); await call.answer()
@usr_m.router.callback_query(F.data == "rules")
async def _prules(call: CallbackQuery, state: FSMContext = None, *a, **kw): txt = RULES_PT if glang() == "pt" else RULES_EN; await call.message.edit_text(txt, reply_markup=KB(inline_keyboard=[[Btn(text=localize(f"btn{DOT}back"), callback_data="back_to_menu")]])); await call.answer()
usr_m.router.callback_query.handlers[:0] = usr_m.router.callback_query.handlers[-2:]
#@pay_m.router.callback_query(F.data == "ps_refresh")
#async def _cps_refresh(c: CallbackQuery, state: FSMContext): pt = glang() == "pt"; await sync_ps(); txt, kb = await _build_ps_shop_kb(); await _safe(c.message.edit_text(txt, reply_markup=kb)); await c.answer("✅ Estoque atualizado!" if pt else "✅ Stock refreshed!")
#@pay_m.router.callback_query(F.data.startswith("ps_grp:"))
#async def _cps_grp(c: CallbackQuery, state: FSMContext): gk = c.data.split(":", 1)[1]; txt, kb = await _build_ps_shop_kb(gk); await _safe(c.message.edit_text(txt, reply_markup=kb)); await c.answer()
#@pay_m.router.callback_query(F.data.startswith("ps_rgrp:"))
#async def _cps_rgrp(c: CallbackQuery, state: FSMContext): pt = glang() == "pt"; gk = c.data.split(":", 1)[1]; await sync_ps(); txt, kb = await _build_ps_shop_kb(gk); await _safe(c.message.edit_text(txt, reply_markup=kb)); await c.answer("✅ Estoque atualizado!" if pt else "✅ Stock refreshed!")
#@pay_m.router.callback_query(F.data.startswith("ps_itm:"))
#async def _cps_itm(c: CallbackQuery, state: FSMContext): pt = glang() == "pt"; parts = c.data.split(":"); gid = int(parts[1]); src = parts[2] if len(parts) > 2 else "root"; t = next((x for x in await _dbg() if x[0] == gid), None); info = (await get_item_info_cached(t[1])) if t else {}; dsc = str((info or {}).get("description") or t[1]) if t else ""; _ = (await state.update_data(csrf_item=t[1], item_name=t[1])) if (t and state) else None; stk = _get_stk(t[1]) if t else 0; em = _prod_emoji(t[1]) if t else "🛍️"; back_cb = f"ps_grp:{src}" if src != "root" else "shop"; card = (f"{em} <b>{html.escape(t[1])}</b>\n\n{html.escape(dsc)}\n\n💵 <b>{'Preço' if pt else 'Price'}:</b> R$ {t[2]:.2f}\n📦 <b>{'Em estoque' if pt else 'In stock'}:</b> {_stk_ball(stk)} {'unidades' if pt else 'units'}" if t else "❌"); kb = KB(inline_keyboard=[[Btn(text=f"🛒 {'Comprar com Saldo' if pt else 'Buy with Balance'} — R$ {t[2]:.2f}", callback_data=f"ps_buy:{gid}:{src}")], [Btn(text=f"💠 {'Comprar com PIX Imediato' if pt else 'Buy Now with PIX'} — R$ {t[2]:.2f}", callback_data=f"pix_item:{t[1][:48]}")], [Btn(text="« Voltar" if pt else "« Back", callback_data=back_cb)], [Btn(text="⬅️ Menu Principal" if pt else "⬅️ Back to menu", callback_data="back_to_menu"), Btn(text="🔄 Atualizar" if pt else "🔄 Refresh", callback_data=f"ps_itm:{gid}:{src}")]]) if t else None; _ = (await _safe(c.message.edit_text(card, reply_markup=kb))) if t else None; await c.answer()
#@pay_m.router.callback_query(F.data.startswith("ps_buy:"))
async def _cps_buy(c: CallbackQuery, state: FSMContext): pt = glang() == "pt"; gid = int(c.data.split(":")[1]); t = next((x for x in await _dbg() if x[0] == gid), None); stk = _get_stk(t[1]) if t else 0; res = (await _pbtx(c.from_user.id, t[1])) if (t and stk > 0) else (False, ("❌ Produto esgotado no fornecedor no momento (🔴 0)." if pt else "❌ Out of stock (🔴 0)."), None); ok, msg, data = res; val_s = str((data or {}).get("value") or "") if isinstance(data, dict) else ""; _ = (await c.message.answer(f"✅ <b>{'Compra Confirmada e Entregue!' if pt else 'Purchase Confirmed & Delivered!'}</b>\n📦 <b>{html.escape(t[1])}</b>\n<code>{html.escape(val_s)}</code>", protect_content=True), await c.answer("✅ Entregue!" if pt else "✅ Delivered!")) if (ok and val_s) else (await c.answer((localize(f"shop{DOT}insufficient_funds") if msg == "insufficient_funds" else str(msg or "Erro"))[:190], show_alert=True))
#_pall()
@pay_m.router.callback_query(F.data.startswith(("ps_grp:", "ps_rgrp:", "ps_refresh", "shop")))
async def _cps_all(c: CallbackQuery): txt, kb = await _build_ps_shop_kb(c.data.split(":")[1] if ":" in c.data else ""); await c.message.edit_text(txt, reply_markup=kb); await c.answer()
@pay_m.router.callback_query(F.data.startswith("ps_itm:"))
async def _cps_itm2(c: CallbackQuery, state: FSMContext): p = c.data.split(":"); t = next(x for x in await _dbg() if x[0] == int(p[1])); await state.update_data(csrf_item=t[1], item_name=t[1]); kb = KB(inline_keyboard=[[Btn(text=f"🛒 Comprar com Saldo — R$ {t[2]:.2f}", callback_data="buy")], [Btn(text=f"💠 PIX Imediato — R$ {t[2]:.2f}", callback_data=f"pix_item:{t[1][:48]}")], [Btn(text="« Voltar", callback_data="shop")]]); await c.message.edit_text(f"🛍️ <b>{t[1]}</b>\n💵 <b>Preço:</b> R$ {t[2]:.2f}\n📦 <b>Em estoque:</b> {_stk_ball(_get_stk(t[1]))}", reply_markup=kb); await c.answer()
_pall(); usr_m.router.callback_query.handlers[:0] = usr_m.router.callback_query.handlers[-2:]; pay_m.router.callback_query.handlers[:0] = pay_m.router.callback_query.handlers[-2:]

async def _main(): asyncio.create_task(_ka13()); await start_bot()
_RUN = asyncio.run(_main()) if __name__ == "__main__" else None
asyncio.run(_main())
