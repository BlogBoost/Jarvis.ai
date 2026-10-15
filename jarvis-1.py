#!/usr/bin/env python3
"""J.A.R.V.I.S. для Android (Termux). Слушает голос, понимает команды, управляет телефоном."""
import json, os, re, subprocess, sys, time, urllib.request

MODEL = "claude-sonnet-5-5"
KEY_FILE = os.path.expanduser("~/.jarvis_key")
API_KEY = os.environ.get("ANTHROPIC_API_KEY") or (open(KEY_FILE).read().strip() if os.path.exists(KEY_FILE) else "")

APPS = {
    "youtube": "com.google.android.youtube", "ютуб": "com.google.android.youtube",
    "telegram": "org.telegram.messenger", "телеграм": "org.telegram.messenger",
    "whatsapp": "com.whatsapp", "ватсап": "com.whatsapp",
    "chrome": "com.android.chrome", "хром": "com.android.chrome",
    "карты": "com.google.android.apps.maps", "maps": "com.google.android.apps.maps",
    "spotify": "com.spotify.music", "спотифай": "com.spotify.music",
    "instagram": "com.instagram.android", "инстаграм": "com.instagram.android",
    "вк": "com.vkontakte.android", "vk": "com.vkontakte.android",
    "gmail": "com.google.android.gm", "почта": "com.google.android.gm",
    "play market": "com.android.vending", "плей маркет": "com.android.vending",
    "tiktok": "com.zhiliaoapp.musically", "тикток": "com.zhiliaoapp.musically",
}

SYSTEM = """Ты — J.A.R.V.I.S., ИИ-ассистент Тони Старка, живущий в телефоне пользователя на Android. Обращайся «сэр». Тон вежливый, спокойный, с сухим британским юмором. Говори по-русски, коротко (1–2 предложения), без markdown: ответ озвучивается.
Верни ТОЛЬКО JSON: {"say": "что произнести", "actions": [ ... ]}
Доступные действия (поле "do"):
open_app {"arg": "название или package"}, open_url {"arg": "url"}, search {"arg": "запрос"},
torch {"arg": "on|off"}, volume {"arg": 0-100}, brightness {"arg": 0-100}, wifi {"arg": "on|off"},
call {"arg": "имя или номер"}, sms {"arg": "имя или номер", "text": "текст"},
alarm {"arg": "HH:MM"}, timer {"arg": секунды}, battery {}, camera {}, settings {}, vibrate {}.
Если действий не нужно — "actions": []. Не выдумывай результаты: для battery просто скажи, что проверяешь."""

def sh(cmd, inp=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, input=inp)
        return r.stdout.strip()
    except Exception as e:
        return ""

def say(text):
    print("JARVIS:", text)
    sh(["termux-tts-speak", "-l", "ru", "-p", "0.75", "-r", "0.95", text])

def listen():
    print("\n🎤 Слушаю...")
    return sh(["termux-speech-to-text"]).strip()

def find_contact(name):
    if re.fullmatch(r"[+\d\s\-()]{5,}", name):
        return re.sub(r"[\s\-()]", "", name)
    try:
        for c in json.loads(sh(["termux-contact-list"]) or "[]"):
            if name.lower() in c.get("name", "").lower():
                return c.get("number")
    except Exception:
        pass
    return None

def am(*args):
    return sh(["am", "start", *args])

def do(act):
    d, arg = act.get("do"), act.get("arg")
    if d == "open_app":
        pkg = APPS.get(str(arg).lower(), arg)
        am("--user", "0", "-p", pkg, "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER")
    elif d == "open_url":
        sh(["termux-open-url", str(arg)])
    elif d == "search":
        sh(["termux-open-url", "https://www.google.com/search?q=" + urllib.request.quote(str(arg))])
    elif d == "torch":
        sh(["termux-torch", str(arg)])
    elif d == "volume":
        sh(["termux-volume", "music", str(round(int(arg) * 15 / 100))])
    elif d == "brightness":
        sh(["termux-brightness", str(round(int(arg) * 255 / 100))])
    elif d == "wifi":
        sh(["termux-wifi-enable", "true" if arg == "on" else "false"])
    elif d == "call":
        n = find_contact(str(arg))
        if n: sh(["termux-telephony-call", n])
        else: say("Контакт не найден, сэр.")
    elif d == "sms":
        n = find_contact(str(arg))
        if n: sh(["termux-sms-send", "-n", n, act.get("text", "")])
        else: say("Контакт не найден, сэр.")
    elif d == "alarm":
        h, m = str(arg).split(":")
        am("-a", "android.intent.action.SET_ALARM", "--ei", "android.intent.extra.alarm.HOUR", str(int(h)),
           "--ei", "android.intent.extra.alarm.MINUTES", str(int(m)), "--ez", "android.intent.extra.alarm.SKIP_UI", "true")
    elif d == "timer":
        am("-a", "android.intent.action.SET_TIMER", "--ei", "android.intent.extra.alarm.LENGTH", str(int(arg)),
           "--ez", "android.intent.extra.alarm.SKIP_UI", "true")
    elif d == "battery":
        try:
            b = json.loads(sh(["termux-battery-status"]))
            say(f"Заряд {b['percentage']} процентов, сэр.")
        except Exception:
            say("Не удалось узнать заряд, сэр.")
    elif d == "camera":
        am("-a", "android.media.action.STILL_IMAGE_CAMERA")
    elif d == "settings":
        am("-a", "android.settings.SETTINGS")
    elif d == "vibrate":
        sh(["termux-vibrate", "-d", "300"])

# ---------- Режим без ИИ (если нет ключа) ----------
def local(text):
    t = text.lower()
    if m := re.search(r"(?:открой|запусти|включи)\s+(.+)", t):
        name = m.group(1).strip()
        if "фонарик" in name: return "Включаю, сэр.", [{"do": "torch", "arg": "on"}]
        if name in APPS: return f"Открываю {name}, сэр.", [{"do": "open_app", "arg": name}]
    if "выключи фонарик" in t: return "Готово, сэр.", [{"do": "torch", "arg": "off"}]
    if m := re.search(r"громкост\w*\s+(?:на\s+)?(\d+)", t): return "Сделано, сэр.", [{"do": "volume", "arg": int(m.group(1))}]
    if m := re.search(r"яркост\w*\s+(?:на\s+)?(\d+)", t): return "Сделано, сэр.", [{"do": "brightness", "arg": int(m.group(1))}]
    if m := re.search(r"позвони\s+(.+)", t): return "Набираю, сэр.", [{"do": "call", "arg": m.group(1)}]
    if m := re.search(r"будильник\s+на\s+(\d{1,2})[:\s](\d{2})", t): return "Будильник установлен, сэр.", [{"do": "alarm", "arg": f"{m.group(1)}:{m.group(2)}"}]
    if "батаре" in t or "заряд" in t: return "Проверяю.", [{"do": "battery"}]
    if "врем" in t: return "Сейчас " + time.strftime("%H:%M") + ", сэр.", []
    if m := re.search(r"(?:найди|поищи)\s+(.+)", t): return "Ищу, сэр.", [{"do": "search", "arg": m.group(1)}]
    return "Не понял команду, сэр. Для свободного разговора нужен ключ API.", []

# ---------- Режим с ИИ ----------
hist = []
def ai(text):
    hist.append({"role": "user", "content": text})
    body = json.dumps({"model": MODEL, "max_tokens": 500, "system": SYSTEM, "messages": hist[-10:]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", body,
        {"content-type": "application/json", "x-api-key": API_KEY, "anthropic-version": "2023-06-01"})
    out = json.load(urllib.request.urlopen(req, timeout=30))["content"][0]["text"]
    hist.append({"role": "assistant", "content": out})
    m = re.search(r"\{.*\}", out, re.S)
    j = json.loads(m.group(0)) if m else {"say": out, "actions": []}
    return j.get("say", ""), j.get("actions", [])

def main():
    mode = "ИИ" if API_KEY else "локальные команды (нет ключа API)"
    say(f"Системы запущены, сэр. Режим: {mode}. Скажите «Джарвис, отбой», чтобы завершить.")
    while True:
        text = listen()
        if not text:
            continue
        print("ВЫ:", text)
        if re.search(r"отбой|выход|стоп", text.lower()):
            say("Отключаюсь, сэр."); break
        try:
            reply, actions = ai(text) if API_KEY else local(text)
        except Exception as e:
            reply, actions = "Связь с ИИ потеряна, сэр.", []
            print("Ошибка:", e)
        if reply: say(reply)
        for a in actions:
            try: do(a)
            except Exception as e: print("Ошибка действия:", a, e)

if __name__ == "__main__":
    main()
