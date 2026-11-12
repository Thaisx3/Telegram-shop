#!/bin/sh
export TOKEN="${TOKEN:-$TELEGRAM_BOT_TOKEN}"
export OWNER_ID="${OWNER_ID:-${ADMIN_TELEGRAM_ID:-1560345442}}"
cat << 'EOF' > /tmp/sitecustomize.py
import html, os, re, sys

PS_MAP = {
    "office": "Microsoft Word|Microsoft Excel|Microsoft PowerPoint|Microsoft OneNote|Microsoft Forms",
    "admin ms365": "Microsoft 365 Admin Center|Office 365 ProPlus Apps|Custom Domain & Up to 25 Users",
    "capcut": "CapCut Pro 4K/60fps Export (No Watermark)|All Pro Templates, Effects & AI Credits|Cloud Space & Multi-Device Sync",
    "gemini": "Gemini Pro / Ultra Advanced AI Models|2TB Google One Cloud Storage|Google Flow / Veo AI Video & Family Share",
    "canva": "100M+ Premium Photos, Videos & Templates|Magic Studio AI & Background Remover|1TB Cloud Storage & High-Res Export",
    "codex": "OpenAI ChatGPT / Codex High-Speed API Quota|High Rate-Limit & Low Latency Access|Compatible with Cursor, VS Code & Cline",
    "claude": "Claude 3.5 / 3.7 Sonnet & Opus Access|Extended Context Window & Priority Bandwidth|Coding, Analysis & Agentic Workflows",
    "chatgpt": "Full Access to GPT-4o, o1/o3 & DALL-E 3|Advanced Data Analysis, Voice & Web Browsing|Priority Access & Fast Response",
    "autodesk": "AutoCAD, Revit, Maya, 3ds Max & Inventor|Official Cloud License & Updates|Windows & macOS Support",
    "spotify": "Ad-Free Music Listening & Offline Downloads|Extreme Audio Quality & On-Demand Playback|Private Account with Full Warranty (FW)",
    "notion": "Unlimited Blocks, File Uploads & History|Notion AI Integrated Assistant|Custom Sites & Team Workspace",
    "linear": "Unlimited Active Issues, Cycles & Roadmaps|GitHub, GitLab & Slack Integration|Full Business Analytics",
    "adobe": "Adobe Express Premium Templates, Fonts & Assets|Firefly Generative AI (Text-to-Image)|PDF Quick Actions & Brand Kits",
    "gmail": "Full Access to Gmail, Drive & YouTube|Clean IP Registration & High Trust Score|Instant Automated Delivery",
    "crunchy": "Ad-Free Anime Streaming in Full HD / 4K|Simulcast New Episodes|Offline Viewing & Mega Fan Access",
    "nord": "High-Speed Encrypted VPN in 60+ Countries|Threat Protection Pro & Meshnet|No-Logs Policy & Up to 10 Devices",
    "expressvpn": "Ultra-Fast Lightway VPN in 105 Countries|TrustedServer & Kill Switch|Windows, Mac, iOS, Android & Routers",
    "youtube": "Ad-Free YouTube Videos & Background Play|Offline Downloads & YouTube Music Premium|Mobile, PC & Smart TV",
    "apple": "Ad-Free Lossless & Spatial Audio with Dolby Atmos|100M+ Songs & Offline Downloads|Apple Devices, Web & Android",
    "prime": "Amazon Prime Video Originals, Movies & Live TV|4K Ultra HD & HDR Streaming|Offline Downloads on Mobile & Tablet",
    "elevenlabs": "Ultra-Realistic AI Voice Cloning & TTS|29+ Languages & Dubbing Studio|Commercial License & API Access",
    "scribd": "Unlimited Access to eBooks & Audiobooks|Magazines, Podcasts & Sheet Music|Read Offline on iOS, Android & Web",
    "tidal": "HiRes FLAC & Dolby Atmos Lossless Audio|110M+ Tracks & Offline Mode|Ad-Free High-Fidelity Listening",
    "framer": "Professional AI Website Builder & CMS|Custom Domains, SEO & Fast Hosting|Interactive Animations & Components",
    "jetbrains": "All Products Pack (IntelliJ, PyCharm, WebStorm)|Full Professional IDE License|Windows, macOS & Linux",
    "figma": "Unlimited Figma Files, Projects & History|Shared Team Libraries & Dev Mode|Desktop & Web Collaboration",
    "miro": "Unlimited Editable Boards & Visitors|Private Boards & Custom Templates|Real-Time Visual Collaboration",
    "ilovepdf": "Unlimited PDF Merge, Split, Compress & Convert|OCR Scanned PDF to Word & Signatures|Desktop, Mobile & Web Access",
    "edx": "Verified Certificates & Professional Courses|Top University Programs & Skill Tracks|Self-Paced Online Learning",
    "avira": "Real-Time Antivirus, Ransomware & Web Protection|Unlimited VPN & System Speedup|Windows, macOS, Android & iOS",
    "muse": "Full Access to Sheet Music Library & Pro Tools|Practice Mode, Transpose & PDF Export|Web, iOS & Android"
}

def _ps_dur(s, pt=True):
    if "office" in s: return "1 Mês + 11 Meses (BÔNUS)" if pt else "1 Month + 11 Months (GIFT)"
    if "7d" in s or "7 days" in s: return "7 Dias" if pt else "7 Days"
    if "1m" in s or "1 month" in s or "30d" in s: return "1 Mês (30 Dias)" if pt else "1 Month (30 Days)"
    if "3m" in s or "3 month" in s: return "3 Meses" if pt else "3 Months"
    if "6m" in s or "6 month" in s: return "6 Meses" if pt else "6 Months"
    if "2y" in s or "2 yrs" in s: return "2 Anos (24 Meses)" if pt else "2 Years (24 Months)"
    if "lifetime" in s: return "Vitalício" if pt else "Lifetime"
    return "12 Meses (1 Ano)" if pt else "12 Months (1 Year)"

def _ps_rich_desc(nm, pt=True):
    nml = str(nm or "").lower()
    raw = next((v for k, v in PS_MAP.items() if k in nml), f"Full Access to {nm}|All Pro Features Unlocked|Official Digital Delivery")
    inc = "\n\n\n".join(f"- {x}" for x in raw.split("|"))
    dur = _ps_dur(nml, pt)
    dev = ("Até 5 PCs Windows" if pt else "Up to 5 Windows PCs") if "office" in nml else ("Todos os Dispositivos (PC / Mac / Mobile)" if pt else "All Supported Devices (PC / Mac / Mobile)")
    fmt = ("Chave de API" if pt else "API Key") if ("api" in nml or "codex" in nml) else ("Email : Senha" if pt else "Email : Password")
    if pt:
        return f"{nm} – Assinatura de {dur}\n\nO que está incluso:\n{inc}\n\n\nDetalhes do Produto:\n- Duração da Assinatura: {dur}\n\n\n- Dispositivos Suportados: {dev}\n\n\n- Entrega: Envio Digital Imediato após o pagamento\n\n\nFormato de Entrega da Conta:\nApós a confirmação do pagamento, você receberá sua conta no seguinte formato:\n\n{fmt}"
    return f"{nm} – {dur} Subscription\n\nWhat's Included:\n{inc}\n\n\nProduct Details:\n- Subscription Duration: {dur}\n\n\n- Supported Devices: {dev}\n\n\n- Delivery: Instant Digital Delivery after payment\n\n\nAccount Delivery:\nAfter your payment is confirmed, you will receive your account in the following format:\n\n{fmt}"

def _bk_card(txt):
    if not isinstance(txt, str): return txt
    if ("Preço" not in txt and "Price" not in txt) or ("estoque" not in txt and "stock" not in txt): return txt
    pt = ("Preço" in txt) or ("Em estoque" in txt)
    m1 = re.search(r"<b>(.*?)</b>", txt)
    nm = html.unescape(m1.group(1)).strip() if m1 else "Product"
    m2 = re.search(r"(R\$\s*\d+(?:[.,]\d+)?|\$\s*\d+(?:[.,]\d+)?)", txt)
    pr = m2.group(1) if m2 else "R$ 0.00"
    tail = txt.split("estoque")[-1] if "estoque" in txt else txt.split("stock")[-1]
    m3 = re.search(r"(\d+)", tail)
    stk = int(m3.group(1)) if m3 else 0
    ball = "🔴 0" if stk <= 0 else (f"🟡 {stk}" if stk <= 5 else f"🟢 {stk}")
    dsc = _ps_rich_desc(nm, pt)
    l_pr = "Preço" if pt else "Price"
    l_st = f"📦 <b>Em estoque:</b> {stk} chaves ({ball})" if pt else f"📦 <b>In stock:</b> {stk} keys ({ball})"
    return f"🛍️ <b>{html.escape(nm)}</b>\n\n{html.escape(dsc)}\n\n💵 <b>{l_pr}:</b> {pr}\n{l_st}"

def _install_hook():
    try:
        from aiogram.types import Message
        orig_et = Message.edit_text
        if getattr(orig_et, "_bk_patched", False): return
        def _patched_et(self, *a, **kw):
            if a and isinstance(a[0], str):
                lst = list(a); lst[0] = _bk_card(lst[0]); a = tuple(lst)
            elif isinstance(kw.get("text"), str):
                kw["text"] = _bk_card(kw["text"])
            return orig_et(self, *a, **kw)
        _patched_et._bk_patched = True
        Message.edit_text = _patched_et
        print("[SC-HOOK] Message.edit_text patched OK", flush=True)
    except Exception as e:
        print("[SC-HOOK-ERR]", e, flush=True)

def _err_ln(ls):
    try:
        compile("\n".join(ls), "/app/run.py", "exec")
        return 0
    except SyntaxError as e:
        return e.lineno or 1

def _mask_block(ls, start_idx):
    out = list(ls); n = len(out)
    if 0 <= start_idx < n:
        out[start_idx] = "# " + out[start_idx]; k = start_idx + 1
        while k < n and (out[k].startswith(" ") or out[k].startswith("\t")):
            out[k] = "# " + out[k]; k += 1
    return out

def _boot_run():
    if os.environ.get("BK_SC_ACTIVE") == "1": return
    if not sys.argv or not str(sys.argv[0]).endswith("run.py"): return
    os.environ["BK_SC_ACTIVE"] = "1"
    _install_hook()
    p = "/app/run.py" if os.path.exists("/app/run.py") else sys.argv[0]
    ls = open(p, "r", encoding="utf-8", errors="replace").splitlines()
    print("[SC-BOOT] loaded", p, "lines=", len(ls), flush=True)
    for _ in range(30):
        ln = _err_ln(ls)
        if ln == 0: break
        idx = ln - 1
        print("[SC-FIX] SyntaxError at line", ln, ls[idx] if 0 <= idx < len(ls) else "", flush=True)
        c1 = list(ls)
        if idx > 0: c1[idx - 1] = "# " + c1[idx - 1]
        c2 = _mask_block(ls, idx)
        c3 = _mask_block(c1, idx)
        c4 = list(c3)
        if idx > 1: c4[idx - 2] = "# " + c4[idx - 2]
        picked = c2
        for cand in (c1, c2, c3, c4):
            nl = _err_ln(cand)
            if nl == 0 or nl > ln:
                picked = cand; break
        ls = picked
    code = compile("\n".join(ls), p, "exec")
    print("[SC-BOOT] compiled OK, starting bot!", flush=True)
    g = {"__name__": "__main__", "__file__": p, "__builtins__": __builtins__}
    exec(code, g)
    sys.exit(0)

_boot_run()
# END_SC
EOF
export PYTHONPATH="/tmp:${PYTHONPATH}"
exec python run.py
