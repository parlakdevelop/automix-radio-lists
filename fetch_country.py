#!/usr/bin/env python3
"""
countries/<kod>.json dosyalarını Radio-Browser API'den otomatik üretir.

Kullanım:
    pip install requests
    python fetch_country.py TR Turkey
    python fetch_country.py DE Germany
    python fetch_country.py US "United States"

Bu, elle link toplamak yerine Radio-Browser'ın her gün otomatik test
ettiği (LastCheckOK) canlı/çalışan istasyonları çeker — böylece bozuk
link riski çok düşük olur. Çıktıyı countries/<kod küçük harf>.json'a
yazar; sen de commit/push edersin.

İstersen bunu bir GitHub Action'a bağlayıp haftalık otomatik
çalıştırabiliriz (aşağıda örnek workflow var).
"""
import json
import os
import re
import sys
import requests

# Radio-Browser'ın resmi mirror sunucularından biri. Down olursa
# de2.api.radio-browser.info / fr1.api.radio-browser.info gibi
# alternatiflerini deneyebilirsin.
API_BASE = "https://de1.api.radio-browser.info/json"
USER_AGENT = "AutoMix-RadioListBuilder/1.0"

LIMIT = 60  # Ham olarak kaç kayıt çekilsin — tekilleştirmeden ÖNCEki sayı.
            # Aynı istasyonun 2-3 kopyası olabildiği için hedeften (~20-25
            # benzersiz istasyon) yüksek tutuyoruz.


def _normalize_name(name: str) -> str:
    """'Power FM 128k', 'Power FM (HQ)', 'POWER FM' gibi varyasyonların
    hepsini aynı istasyon olarak tanımak için isim normalize edilir:
    küçük harfe çevir, parantez/bitrate/kalite eklerini at, boşlukları sadeleştir."""
    n = name.lower().strip()
    n = re.sub(r'\(.*?\)', '', n)              # (HQ), (128k) gibi parantezleri at
    n = re.sub(r'\b\d{2,3}\s*k(bps)?\b', '', n)  # "128k", "128 kbps" at
    n = re.sub(r'\b(hd|hq|aac|mp3|stereo)\b', '', n)  # kalite etiketlerini at
    n = re.sub(r'[^a-z0-9ığüşöç ]', '', n)       # noktalama at
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def fetch_country(country_code: str, country_name: str):
    url = f"{API_BASE}/stations/bycountrycodeexact/{country_code.upper()}"
    params = {
        "order": "clickcount",
        "reverse": "true",
        "hidebroken": "true",   # Radio-Browser'ın bozuk işaretlediklerini atla
        "limit": LIMIT,
    }
    headers = {"User-Agent": USER_AGENT}

    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    stations = resp.json()

    result = []
    seen_urls = set()
    seen_names = set()
    for s in stations:
        stream_url = s.get("url_resolved") or s.get("url") or ""
        raw_name = (s.get("name") or "").strip()
        if not stream_url or not raw_name:
            continue
        if s.get("lastcheckok") == 0:
            continue  # Radio-Browser son kontrolde çalışmadığını işaretlemiş

        norm_name = _normalize_name(raw_name)
        if stream_url in seen_urls or norm_name in seen_names:
            # Aynı istasyonun başka bir bitrate/link kopyası — çünkü
            # sonuçlar clickcount'a göre sıralı, ilk gördüğümüz (en
            # popüler kopya) zaten alındı, bunu atlıyoruz.
            continue
        seen_urls.add(stream_url)
        seen_names.add(norm_name)

        result.append({
            "name": raw_name,
            "url": stream_url,
            "country": country_code.upper(),
            "favicon": s.get("favicon", "") or "",
            "codec": (s.get("codec") or "MP3").upper(),
            "bitrate": s.get("bitrate", 0) or 0,
        })

        if len(result) >= 25:  # tekilleştirmeden SONRA istediğimiz hedef sayı
            break

    out_path = f"countries/{country_code.lower()}.json"
    os.makedirs("countries", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"{len(result)} benzersiz istasyon yazıldı -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Kullanım: python fetch_country.py <ÜLKE_KODU> <Radio-Browser Ülke Adı>")
        print('Örnek:    python fetch_country.py TR Turkey')
        sys.exit(1)

    fetch_country(sys.argv[1], sys.argv[2])
