import asyncio, html, sqlite3, sys
import run
import bot.i18n.strings as i18n_s, bot.i18n.main as i18n_m
from aiogram import F
from aiogram.types import CallbackQuery, InlineKeyboardButton as Btn, InlineKeyboardMarkup as KB, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.misc import EnvKeys
from bot.i18n import localize

DOT = chr(46)
CFG_DB = f"runtime_cfg{DOT}db"
def _cget(k: str, d: str = "") -> str:
    with sqlite3.connect(CFG_DB) as c:
        c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)")
        r = c.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        return r[0] if r and r[0] else d
def _cset(k: str, v: str):
    with sqlite3.connect(CFG_DB) as c:
        c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)")
        c.execute("INSERT OR REPLACE INTO kv VALUES (?, ?)", (k, v.strip()))

PT_MAP = {"menu.title": "⛩️ Menu Principal — Brazil Key", "btn.shop": "🛍️ Loja", "btn.rules": "📜 Regras", "btn.profile": "👤 Perfil", "btn.support": "🆘 Suporte", "btn.channel": "📢 Canal", "btn.admin_menu": "🎛️ Painel Admin", "btn.back": "⬅️ Voltar", "btn.to_menu": "🏠 Menu Principal", "btn.close": "❌ Fechar", "btn.buy": "💳 Comprar", "btn.search": "🔍 Buscar no catálogo", "btn.cart": "🛒 Carrinho", "btn.replenish": "💰 Recarregar saldo", "btn.purchased": "📦 Compras realizadas", "btn.referral": "🤝 Afiliados", "btn.check_payment": "✅ Verificar pagamento", "btn.pay": "💳 Pagar", "payments.method_choose": "💳 Escolha a forma de pagamento:", "payments.replenish_prompt": "💰 Digite o valor da recarga em {currency}:", "shop.categories.title": "📂 Escolha uma categoria:", "admin.menu.main": "🎛️ Painel de Administração — Brazil Key"}
EN_ORIG = dict(i18n_s.TRANSLATIONS.get("en", {}))
PT_DICT = {k: (v.replace("Main menu", "Menu Principal").replace("Shop", "Loja").replace("Profile", "Perfil").replace("Balance", "Saldo").replace("Cart", "Carrinho").replace("Purchases", "Compras").replace("Back", "Voltar").replace("Search", "Buscar").replace("Category", "Categoria").replace("Price", "Preço").replace("In stock", "Em estoque").replace("Unlimited", "Ilimitado").replace("Admin panel", "Painel Admin") if isinstance(v, str) else v) for k, v in EN_ORIG.items()}
PT_DICT.update(PT_MAP)
i18n_s.TRANSLATIONS["pt"] = PT_DICT

def _glng() -> str:
    return _cget("lang", "pt")

def _apply_lang(l: str):
    _cset("lang", l)
    EnvKeys.BOT_LOCALE = l
    if hasattr(i18n_m, "DEFAULT_LOCALE"): i18n_m.DEFAULT_LOCALE = l
    if hasattr(i18n_m, "get_locale"): i18n_m.get_locale = lambda: l
    if "en" in i18n_s.TRANSLATIONS:
        i18n_s.TRANSLATIONS["en"].update(PT_DICT if l == "pt" else EN_ORIG)

_apply_lang(_glng())
if _cget("pp_tok"): run.PP_TOK = _cget("pp_tok")
if _cget("ps_key"): run.PS_KEY = _cget("ps_key")
if _cget("cp_tok"): EnvKeys.CRYPTO_PAY_TOKEN = _cget("cp_tok")

_orig_mm = run.kb_m.main_menu
def _mm(role: int, channel: str | None = None, helper: str | None = None) -> KB:
    rows = list(_orig_mm(role, channel, helper).inline_keyboard)
    rows.append([Btn(text="🌐 Idioma: 🇧🇷 PT-BR | 🇺🇸 EN-US" if _glng() == "pt" else "🌐 Language: 🇺🇸 EN-US | 🇧🇷 PT-BR", callback_data="lang_sel")])
    return KB(inline_keyboard=rows)

_orig_akb = run.kb_m.admin_console_keyboard
def _akb(*a, **kw) -> KB:
    rows = list(_orig_akb(*a, **kw).inline_keyboard)
    rows.insert(0, [Btn(text="🔑 Configurar Chaves API (PushinPay / ProdSeller)" if _glng() == "pt" else "🔑 Configure API Keys (PushinPay / ProdSeller)", callback_data="adm_api")])
    rows.insert(1, [Btn(text="🌐 Idioma: 🇧🇷 PT-BR / 🇺🇸 EN-US" if _glng() == "pt" else "🌐 Language: 🇺🇸 EN-US / 🇧🇷 PT-BR", callback_data="lang_sel")])
    return KB(inline_keyboard=rows)

for mn, mo in list(sys.modules.items()):
    if mn.startswith("bot") and mo is not None:
        if hasattr(mo, "main_menu"): setattr(mo, "main_menu", _mm)
        if hasattr(mo, "admin_console_keyboard"): setattr(mo, "admin_console_keyboard", _akb)

class ApiFSM(StatesGroup):
    pp = State()
    ps = State()
    cp = State()

_kb_lng = lambda: KB(inline_keyboard=[[Btn(text="✅ 🇧🇷 Português (BR)" if _glng() == "pt" else "🇧🇷 Português (BR)", callback_data="set_lng:pt"), Btn(text="✅ 🇺🇸 English (US)" if _glng() == "en" else "🇺🇸 English (US)", callback_data="set_lng:en")], [Btn(text=localize("btn.back"), callback_data="back_to_menu")]])
@run.pay_m.router.callback_query(F.data == "lang_sel")
async def _on_lsel(call: CallbackQuery):
    await call.message.edit_text("🌐 <b>Selecione o Idioma / Select Language:</b>", reply_markup=_kb_lng())
    await call.answer()

@run.pay_m.router.callback_query(F.data.startswith("set_lng:"))
async def _on_slng(call: CallbackQuery):
    l = call.data.split(":")[1]
    _apply_lang(l)
    await call.message.edit_text("✅ Idioma alterado para <b>🇧🇷 Português (Brasil)</b>!" if l == "pt" else "✅ Language changed to <b>🇺🇸 English (USA)</b>!", reply_markup=_kb_lng())
    await call.answer()

_msk = lambda s: f"{s[:6]}...{s[-4:]}" if len(s) > 10 else ("✅ Configurado" if s else "❌ Vazio")
_kb_api = lambda: KB(inline_keyboard=[[Btn(text="💠 Definir Token PushinPay PIX", callback_data="sapi:pp")], [Btn(text="📦 Definir API Key ProdSeller", callback_data="sapi:ps")], [Btn(text="💎 Definir Token CryptoPay", callback_data="sapi:cp")], [Btn(text="🔄 Sincronizar Catálogo ProdSeller", callback_data="sync_ps")], [Btn(text=localize("btn.back"), callback_data="console")]])

@run.pay_m.router.callback_query(F.data == "adm_api")
async def _on_aapi(call: CallbackQuery, state: FSMContext):
    if str(call.from_user.id) != str(EnvKeys.OWNER_ID): return
    await state.clear()
    await call.message.edit_text(f"🔑 <b>Configuração de Chaves API — Painel Admin</b>\n\n💠 <b>PushinPay PIX:</b> <code>{_msk(run.PP_TOK)}</code>\n📦 <b>ProdSeller API:</b> <code>{_msk(run.PS_KEY)}</code>\n💎 <b>CryptoPay API:</b> <code>{_msk(str(EnvKeys.CRYPTO_PAY_TOKEN or ''))}</code>\n\nSelecione qual chave deseja configurar:", reply_markup=_kb_api())
    await call.answer()

@run.pay_m.router.callback_query(F.data.startswith("sapi:"))
async def _on_sapi(call: CallbackQuery, state: FSMContext):
    if str(call.from_user.id) != str(EnvKeys.OWNER_ID): return
    k = call.data.split(":")[1]
    await state.set_state({"pp": ApiFSM.pp, "ps": ApiFSM.ps, "cp": ApiFSM.cp}[k])
    await call.message.edit_text(f"✍️ <b>Envie agora no chat o novo valor da chave ({k.upper()}):</b>", reply_markup=KB(inline_keyboard=[[Btn(text="⬅️ Cancelar", callback_data="adm_api")]]))
    await call.answer()

@run.pay_m.router.message(ApiFSM.pp)
async def _sv_pp(msg: Message, state: FSMContext):
    await state.clear()
    run.PP_TOK = (msg.text or "").strip()
    _cset("pp_tok", run.PP_TOK)
    await msg.answer(f"✅ <b>Token PushinPay atualizado com sucesso!</b> (<code>{_msk(run.PP_TOK)}</code>)", reply_markup=_kb_api())

@run.pay_m.router.message(ApiFSM.ps)
async def _sv_ps(msg: Message, state: FSMContext):
    await state.clear()
    run.PS_KEY = (msg.text or "").strip()
    _cset("ps_key", run.PS_KEY)
    await run._sync_ps()
    await msg.answer(f"✅ <b>API Key ProdSeller salva e catálogo sincronizado!</b> (<code>{_msk(run.PS_KEY)}</code>)", reply_markup=_kb_api())

@run.pay_m.router.message(ApiFSM.cp)
async def _sv_cp(msg: Message, state: FSMContext):
    await state.clear()
    EnvKeys.CRYPTO_PAY_TOKEN = (msg.text or "").strip()
    _cset("cp_tok", EnvKeys.CRYPTO_PAY_TOKEN)
    await msg.answer(f"✅ <b>Token CryptoPay salvo com sucesso!</b> (<code>{_msk(EnvKeys.CRYPTO_PAY_TOKEN)}</code>)", reply_markup=_kb_api())

@run.pay_m.router.callback_query(F.data == "sync_ps")
async def _on_sync(call: CallbackQuery):
    if str(call.from_user.id) != str(EnvKeys.OWNER_ID): return
    await run._sync_ps()
    await call.answer("✅ Catálogo ProdSeller sincronizado!", show_alert=True)

if __name__ == "__main__":
    asyncio.run(run._main())
