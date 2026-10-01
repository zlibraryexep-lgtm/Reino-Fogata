#!/usr/bin/env python3
"""Genera news.json con 3 noticias geopolíticas de medios de la tradición
liberal clásica / escuela austriaca. Pensado para correr a diario en GitHub Actions."""
import json, os, re, html, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

FEEDS = {
    "Mises Institute": ["https://mises.org/feed/blog.rss", "https://mises.org/rss.xml", "https://mises.org/feed"],
    "Antiwar.com": ["https://original.antiwar.com/feed/", "https://www.antiwar.com/blog/feed/"],
    "Libertarian Institute": ["https://libertarianinstitute.org/feed/"],
    "Cato Institute": ["https://www.cato.org/rss/recent-opeds", "https://www.cato.org/rss/commentary"],
    "AIER": ["https://www.aier.org/feed/"],
    "FEE": ["https://fee.org/feed/"],
    "Reason": ["https://reason.com/feed/"],
    "Ron Paul Institute": ["https://ronpaulinstitute.org/feed/"],
}
KW = re.compile(r"\b(war|wars|ukraine|russia\w*|china|chinese|taiwan|iran\w*|israel\w*|gaza|nato|sanctions?|tariffs?|"
                r"empire|foreign policy|military|middle east|venezuela\w*|pentagon|geopolit\w*|brics|treaty|"
                r"sovereignty|syria\w*|north korea\w*|cuba\w*|argentin\w*|milei|european union|trade war|"
                r"ceasefire|invasion|nuclear|diplomacy|embargo)\b", re.I)
UA = {"User-Agent": "Mozilla/5.0 (compatible; CalendarioMedievalBot/1.0)"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "news.json")
UTC = timezone.utc

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return r.read()

def strip(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()

def cut(t, n=220):
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(".,;:") + "…"

def parse_date(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        except Exception:
            return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)

def local(tag):
    return tag.rsplit("}", 1)[-1]

def parse(xml, fuente):
    out = []
    for node in ET.fromstring(xml).iter():
        if local(node.tag) not in ("item", "entry"):
            continue
        d = {}
        for c in node:
            k = local(c.tag)
            if k == "link":
                if c.get("href") and c.get("rel", "alternate") == "alternate":
                    d.setdefault("link", c.get("href"))
                elif c.text and c.text.strip():
                    d.setdefault("link", c.text.strip())
            elif k in ("pubDate", "published", "updated", "date"):
                d.setdefault("date", c.text)
            elif k in ("title", "description", "summary", "encoded", "content"):
                d.setdefault(k, c.text or "")
        link, title = d.get("link", ""), strip(d.get("title"))
        if not title or not link.startswith("http"):
            continue
        resumen = strip(d.get("description") or d.get("summary") or d.get("encoded") or d.get("content"))
        out.append({"titulo": title, "resumen": cut(resumen), "fuente": fuente, "url": link,
                    "dt": parse_date(d.get("date"))})
    return out

def traducir(items):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return
    for it in items:
        try:
            prompt = ("Traduce al español neutral este titular y resumen. Responde SOLO con JSON "
                      '{"titulo":"...","resumen":"..."} sin explicaciones.\n\n'
                      + json.dumps({"titulo": it["titulo"], "resumen": it["resumen"]}, ensure_ascii=False))
            body = json.dumps({"model": "claude-haiku-4-5-20251001", "max_tokens": 500,
                               "messages": [{"role": "user", "content": prompt}]}).encode()
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
                "content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
            txt = json.load(urllib.request.urlopen(req, timeout=60))["content"][0]["text"].strip()
            t = json.loads(re.sub(r"^```(?:json)?|```$", "", txt).strip())
            it["titulo"], it["resumen"], it["traducido"] = t["titulo"], t["resumen"], True
        except Exception as e:
            print("Traducción falló:", e)

def main():
    pool = []
    for fuente, urls in FEEDS.items():
        for u in urls:
            try:
                items = parse(get(u), fuente)
                print(f"OK  {fuente}: {len(items)} entradas ({u})")
                pool += items
                break
            except Exception as e:
                print(f"ERR {fuente}: {u} -> {e}")
    now = datetime.now(UTC)
    geo = [i for i in pool if KW.search(i["titulo"] + " " + i["resumen"])]
    recent = [i for i in geo if i["dt"] and now - i["dt"] <= timedelta(days=4)] or geo
    recent.sort(key=lambda i: i["dt"] or datetime.min.replace(tzinfo=UTC), reverse=True)
    pick, fuentes, vistos = [], set(), set()
    for i in recent:
        if i["fuente"] not in fuentes and i["titulo"] not in vistos:
            pick.append(i); fuentes.add(i["fuente"]); vistos.add(i["titulo"])
        if len(pick) == 3:
            break
    for i in recent:
        if len(pick) == 3:
            break
        if i not in pick and i["titulo"] not in vistos:
            pick.append(i); vistos.add(i["titulo"])
    if not pick:
        print("Sin noticias nuevas: se conserva news.json anterior.")
        if not os.path.exists(OUT):
            json.dump({"actualizado": None, "items": []}, open(OUT, "w", encoding="utf-8"))
        return
    traducir(pick)
    for i in pick:
        dt = i.pop("dt")
        i["fecha"] = dt.date().isoformat() if dt else ""
    json.dump({"actualizado": now.isoformat(timespec="seconds"), "items": pick},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Listo: {len(pick)} noticias.")

if __name__ == "__main__":
    main()
