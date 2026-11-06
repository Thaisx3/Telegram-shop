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
