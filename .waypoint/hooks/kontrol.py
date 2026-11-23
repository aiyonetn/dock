"""Pre-commit denetimleri için saf doğrulama fonksiyonları."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime
from pathlib import Path


# Ağ ve zip modülleri yalnız güncellemede gerekir; her hook'ta yüklenmeleri Python'un açılışını yavaşlatır
# (Windows'ta ~0,2 sn). Kullanan fonksiyonlar kendileri yükler; kontrol.urllib gibi erişimler de çalışmaya devam eder.
_GEC_YUKLENEN = {"http": "http.client", "urllib": "urllib.request", "zipfile": "zipfile"}


def __getattr__(name: str):
    if name in _GEC_YUKLENEN:
        importlib.import_module(_GEC_YUKLENEN[name])
        return sys.modules[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_MOJIBAKE_SOURCE = "\u00e7\u011f\u0131\u00f6\u015f\u00fc\u00c7\u011e\u0130\u00d6\u015e\u00dc\u00e2\u00ee\u00fb\u00c2\u00ce\u00db\u2019\u2018\u201c\u201d\u2013\u2014\u2026\u20ac"
_EMOJI_PREFIX = "\U0001f600".encode("utf-8").decode("cp1252", errors="ignore")[:2]
_MOJIBAKE = tuple(
    dict.fromkeys(
        corrupted
        for char in _MOJIBAKE_SOURCE + _EMOJI_PREFIX
        for encoding in ("cp1252", "cp1254", "latin-1")
        if len(corrupted := char.encode("utf-8").decode(encoding, errors="ignore")) >= 2
        and corrupted != char
    )
)
_BAD_REPLACEMENT = "\ufffd"
_BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp", ".pdf", ".zip", ".gz",
    ".tar", ".7z", ".db", ".sqlite", ".sqlite3", ".woff", ".woff2", ".ttf", ".otf",
    ".eot", ".exe", ".dll", ".so", ".pyc", ".mp3", ".mp4", ".wav", ".mov",
}


def _bad_at(line: str) -> tuple[int, str] | None:
    candidates = [(line.find(_BAD_REPLACEMENT), _BAD_REPLACEMENT)] if _BAD_REPLACEMENT in line else []
    candidates.extend((line.find(pattern), pattern) for pattern in _MOJIBAKE if pattern in line)
    return min(candidates, key=lambda item: item[0]) if candidates else None


def bozuk_metin(name: str, text: str) -> tuple[list[str], list[str]]:
    for line_no, line in enumerate(text.splitlines(), start=1):
        found = _bad_at(line)
        if found is None:
            continue
        position, bad = found
        start, end = max(0, position - 12), min(len(line), position + len(bad) + 12)
        snippet = line[start:position] + repr(line[position:position + len(bad)]) + line[position + len(bad):end]
        return [f"{name}: {line_no}. satırda bozuk karakter var ({snippet}). Dosyayı UTF-8 olarak yeniden yazın; Türkçe harfleri düzeltin."], []
    return [], []


def bozuk_dosya(name: str, data: bytes) -> tuple[list[str], list[str]]:
    normalized = name.replace("\\", "/")
    if ".waypoint/hooks/" in f"/{normalized}/":
        return [], []
    if Path(name).suffix.lower() in _BINARY_EXTENSIONS or b"\x00" in data[:8000]:
        return [], []
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    try:
        decoded = data.decode("utf-8")
    except UnicodeDecodeError:
        return [f"{name}: dosya UTF-8 değil (bozuk bayt). Dosyayı UTF-8 olarak kaydedin."], []
    return bozuk_metin(name, decoded)


def gizli_dosyalar(staged_names: list[str]) -> tuple[list[str], list[str]]:
    """Commit'e eklenen gizli anahtar ve ortam dosyalarını bulur."""
    hatalar: list[str] = []
    for name in staged_names:
        basename = name.replace("\\", "/").rsplit("/", 1)[-1]
        lower = basename.lower()
        sample = lower.endswith((".example", ".sample", ".template"))
        blocked = not sample and (
            (lower.startswith(".env") and lower != ".env.example")
            or lower.endswith((".pem", ".key"))
            or lower.startswith(("id_rsa", "id_ed25519", "id_ecdsa", "id_dsa"))
            or lower in {"credentials.json", "secrets.json", "secrets.yml", "secrets.yaml", ".npmrc", ".pypirc", ".netrc", ".htpasswd"}
            or lower.endswith((".p12", ".pfx", ".jks", ".keystore", ".ppk", ".asc", ".ovpn"))
            or bool(re.fullmatch(r"client_secret.*\.json", lower))
            or bool(re.fullmatch(r"service-account.*\.json", lower))
            or bool(re.fullmatch(r"serviceaccount.*\.json", lower))
            or lower.endswith("-service-account.json")
        )
        if blocked:
            hatalar.append(
                f"{name}: gizli dosyayı commit'ten çıkarın ve .gitignore dosyasına ekleyin."
            )
        elif not sample and re.search(r"\.log(\.\d+)?$", lower):
            hatalar.append(
                f"{name}: günlük (log) dosyası kullanıcı verisi içerebilir; commit'ten çıkarın (git rm --cached) "
                "ve yolunu .gitignore dosyasına ekleyin."
            )
    return hatalar, []


_SECRET_PATTERNS = (
    (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY"), "\u00f6zel anahtar"),
    (re.compile(r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}"), "AWS anahtar\u0131"),
    (re.compile(r"(?<![A-Za-z0-9])(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})"), "GitHub anahtar\u0131"),
    (re.compile(r"(?<![A-Za-z0-9_-])sk-(?:ant-)?[A-Za-z0-9_-]{32,}"), "yapay zek\u00e2 API anahtar\u0131"),
    (re.compile(r"(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack anahtar\u0131"),
    (re.compile(r"(?<![A-Za-z0-9])AIza[0-9A-Za-z_-]{35}"), "Google API anahtar\u0131"),
)
_ASSIGNMENT_SECRET = re.compile(r"(?i)(password|passwd|secret|api_key|apikey|token)\s*[:=]\s*([\"'][^\"'\s]{8,}[\"'])")


_ORNEK_ANAHTAR = ("xxxx", "your", "example", "dummy", "fake", "placeholder", "sahte", "ornek", "örnek")


def gizli_icerik(name: str, text: str) -> tuple[list[str], list[str]]:
    normalized = name.replace("\\", "/")
    basename = normalized.rsplit("/", 1)[-1].lower()
    # Notlar, örnek dosyalar ve hook'lar da taranır, ama yalnız gerçek anahtar imzalarıyla:
    # "password = ..." tahmini oralarda çok yanlış alarm verir.
    imza_yalniz = "/.waypoint/hooks/" in f"/{normalized}/" or basename.endswith((".example", ".sample", ".template", ".md"))
    placeholders = ("xxx", "<", "your", "example", "changeme", "***", "${", "process.env", "os.environ")
    for line_no, line in enumerate(text.splitlines(), 1):
        for pattern, kind in _SECRET_PATTERNS:
            match = pattern.search(line)
            if match and not any(word in match.group(0).lower() for word in _ORNEK_ANAHTAR):
                return [f"{name}: {line_no}. sat\u0131rda gizli anahtar/\u015fifre olabilir ({kind}). Bu de\u011feri dosyadan \u00e7\u0131kar\u0131n, .env gibi kayda girmeyen bir dosyaya ta\u015f\u0131y\u0131n."], []
        if imza_yalniz:
            continue
        match = None if _is_test_file(normalized) else _ASSIGNMENT_SECRET.search(line)  # testlerde sahte şifreler olağan
        if match and not any(value in match.group(2).lower() for value in placeholders):
            return [f"{name}: {line_no}. sat\u0131rda gizli anahtar/\u015fifre olabilir (\u015fifre/anahtar atamas\u0131). Bu de\u011feri dosyadan \u00e7\u0131kar\u0131n, .env gibi kayda girmeyen bir dosyaya ta\u015f\u0131y\u0131n."], []
    return [], []


def _section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("## ") and line[3:].startswith(heading)), None)
    if start is None:
        return ""
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start + 1 : end])


def _eksik_basliklar(text: str, file_name: str, required: tuple[str, ...]) -> list[str]:
    """Zorunlu '## ' başlıklarını arar; başlık bozulursa (ör. 'Şema' → '?ema') denetim boşuna geçmesin."""
    headings = [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]
    return [
        f".waypoint/{file_name}: '{heading}' başlığı eksik; bu başlığı ekleyin (Türkçe harfler bozulduysa dosyayı UTF-8 olarak düzeltin)."
        for heading in required
        if not any(found.startswith(heading) for found in headings)
    ]


def _without_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


HARITA_DOSYA_SINIRI = 30
HARITA_GIRIS_SINIRI = 20


def _harita_maddeleri(text: str, heading: str) -> list[list[str]]:
    """'- a — b — c' satırlarını ['a', 'b', 'c'] olarak döndürür; yorumlar ve '- ...' atlanır."""
    section = _section(_without_html_comments(text), heading)  # açıklamadaki örnek satırlar sayılmaz
    return [
        [part.strip().strip("`").strip() for part in line[2:].split(" — ")]
        for line in section.splitlines()
        if line.startswith("- ") and line.strip() not in {"- ...", "- …"}
    ]


def eski_harita(text: str) -> bool:
    """1.41'den önceki şemalı, fonksiyon fonksiyon biçim."""
    headings = {line[3:].strip() for line in text.splitlines() if line.startswith("## ")}
    return bool(headings & {"Şema", "Key functions / components"}) and "Dosyalar" not in headings


def _kimlik(name: str) -> str:
    """'Kullanici.kaydet()' gibi bir girdi adından koddaki çıplak adı çıkarır: 'kaydet'."""
    return re.split(r"[.:]+", name.split("(", 1)[0].strip())[-1]


def _kelime_var(name: str, text: str) -> bool:
    return bool(re.search(rf"(?<![\w$]){re.escape(name)}(?![\w$])", text))


_BLOK_YORUM = re.compile(r"/\*.*?\*/|<!--.*?-->", re.DOTALL)
_PY_METIN = re.compile(r'""".*?"""|\'\'\'.*?\'\'\'', re.DOTALL)
_SATIR_YORUMU = re.compile(r"^\s*(#(?!\s*define\b)|//|--)")
_SONDAKI_YORUM = re.compile(r"(^|\s)//.*$")


def _yorumsuz(source: str, path: str) -> str:
    """Kaynaktan yorumları kabaca çıkarır: silinmiş bir adın yalnız yorumda kalması 'var' sayılmasın.
    Satır sonundaki '#' yorumları dizelerle karışabildiği için kalır; emin olunamayan yerde ad bulunmuş sayılır."""
    text = _BLOK_YORUM.sub(" ", source)
    python = path.lower().endswith((".py", ".pyw"))
    if python:
        text = _PY_METIN.sub(" ", text)
    lines = []
    for line in text.splitlines():
        if _SATIR_YORUMU.match(line):
            continue
        lines.append(line if python else _SONDAKI_YORUM.sub("", line))  # Python'da '//' tam sayı bölmesidir
    return "\n".join(lines)


def harita(text: str) -> tuple[list[str], list[str]]:
    """Haritanın başlıklarını ve uzunluğunu denetler; uzunluk yalnız uyarıdır, kaydı durdurmaz."""
    if eski_harita(text):
        return [], [
            ".waypoint/HARITA.md eski biçimde (şemalı ve uzun). Bir kez sadeleştirin: yalnız önemli dosyalar ve giriş "
            "noktaları kalsın; biçim komutlar/guncelleme.md dosyasının 7. adımında."
        ]
    hatalar = _eksik_basliklar(text, "HARITA.md", ("Dosyalar", "Giriş noktaları"))
    files = len(_harita_maddeleri(text, "Dosyalar"))
    entries = len(_harita_maddeleri(text, "Giriş noktaları"))
    if files > HARITA_DOSYA_SINIRI or entries > HARITA_GIRIS_SINIRI:
        return hatalar, [
            f".waypoint/HARITA.md uzun: {files} dosya, {entries} giriş noktası (sınır yaklaşık {HARITA_DOSYA_SINIRI} ve "
            f"{HARITA_GIRIS_SINIRI}). Küçük ya da tek yerde kullanılan satırları çıkarın."
        ]
    return hatalar, []


def harita_gercek(text: str, read_file, exists) -> tuple[list[str], list[str]]:
    """Haritadaki her dosya, klasör ve giriş noktasının kayda girecek sürümde var olduğunu doğrular:
    yanlış harita, haritasızlıktan kötüdür. read_file ve exists o sürüme bakar (main: _harita_kaynagi)."""
    if eski_harita(text):
        return [], []
    hatalar: list[str] = []
    for parts in _harita_maddeleri(text, "Dosyalar"):
        if not exists(parts[0]):
            hatalar.append(
                f".waypoint/HARITA.md: '{parts[0]}' kayda girecek sürümde yok; yeni dosyaysa 'git add' ile ekleyin, "
                "taşındıysa yolu düzeltin, silindiyse satırı kaldırın."
            )
    for parts in _harita_maddeleri(text, "Giriş noktaları"):
        if len(parts) < 2:
            hatalar.append(f".waypoint/HARITA.md: '{parts[0]}' satırında dosya yok; biçim: '- ad() — dosya — ne yapar'.")
            continue
        name, path = parts[0], parts[1]
        source = read_file(path)
        if source is None:
            hatalar.append(
                f".waypoint/HARITA.md: '{name}' için yazılan '{path}' dosyası kayda girecek sürümde yok; yeni dosyaysa "
                "'git add' ile ekleyin, değilse yolu proje köküne göre düzeltin ya da kaldırıldıysa satırı silin."
            )
        elif not _kelime_var(_kimlik(name), _yorumsuz(source, path)):
            yorumda = " (adı yalnız yorumda geçiyor)" if _kelime_var(_kimlik(name), source) else ""
            hatalar.append(
                f".waypoint/HARITA.md: '{name}' artık {path} içinde yok{yorumda}; adı ya da dosyası değiştiyse satırı "
                "düzeltin, silindiyse kaldırın."
            )
    return hatalar, []


def dersler(text: str) -> tuple[list[str], list[str]]:
    """Başlıkları denetler; kural ve ders sayısı yalnız uyarıdır, kaydı durdurmaz."""
    hatalar = _eksik_basliklar(text, "DERSLER.md", ("Kurallar", "Kayıtlar"))
    uyarilar = []
    rules = _section(text, "Kurallar")
    count = sum(1 for line in rules.splitlines() if line.startswith("- ") and line != "- ...")
    if count > 20:
        uyarilar.append(f".waypoint/DERSLER.md: Kurallar bölümünde {count} kural var; görev sonunda ya da bitir'de benzer kuralları birleştirip 20'ye indirin.")
    records = _section(text, "Kayıtlar")
    lessons = sum(
        1 for line in records.splitlines()
        if line.startswith("### ") and "YYYY" not in line
    )
    if lessons > 20:
        uyarilar.append(
            f".waypoint/DERSLER.md: Kayıtlar bölümünde {lessons} ders var; görev sonunda ya da bitir'de, kuralı "
            "'Kurallar' bölümünde duran eski dersleri .waypoint/DERS_ARSIV.md dosyasına taşıyın."
        )
    return hatalar, uyarilar


_REQUIRED_HEADINGS = (
    "Proje hedefi", "Aşama", "Nasıl açılır", "Testleri çalıştırma", "Kararlar",
    "Plan", "Şu anki görev", "Sıradaki adım", "Sonra yapılacaklar", "Günlük",
)


def ilerleme(text: str) -> tuple[list[str], list[str]]:
    """Zorunlu başlıkları denetler; bölüm uzunlukları yalnız uyarıdır, kaydı durdurmaz."""
    hatalar = _eksik_basliklar(text, "ILERLEME.md", _REQUIRED_HEADINGS)

    uyarilar = []
    limits = (
        ("Günlük", 10, "Günlük", "kayıt", "en yeni 10 satır kalsın, eskileri .waypoint/ILERLEME_ARSIV.md dosyasının '## Günlük' bölümüne taşıyın."),
        ("Plan", 10, "Plan", "biten görev", "biten görevleri .waypoint/ILERLEME_ARSIV.md dosyasının '## Biten görevler' bölümüne taşıyın."),
        ("Kararlar", 20, "Kararlar", "karar", "en eski kararları .waypoint/ILERLEME_ARSIV.md dosyasının '## Kararlar' bölümüne taşıyın (arşivdeki kararlar geçerliliğini korur)."),
        ("Sonra yapılacaklar", 15, "'Sonra yapılacaklar'", "madde", "kullanıcıya hangilerinden vazgeçildiğini sorun ve onları .waypoint/ILERLEME_ARSIV.md dosyasının '## Vazgeçilen fikirler' bölümüne taşıyın."),
    )
    for heading, warning_limit, label, noun, action in limits:
        section = _section(text, heading)
        if heading == "Plan":
            count = sum(
                1 for line in section.splitlines()
                if line.startswith(("- [x]", "- [X]")) and "YYYY" not in line and line != "- ..."
            )
        else:
            count = sum(
                1 for line in section.splitlines()
                if line.startswith("- ") and "YYYY" not in line and line != "- ..."
            )
        if count > warning_limit:
            uyarilar.append(f".waypoint/ILERLEME.md: {label} bölümünde {count} {noun} var; görev sonunda ya da bitir'de {action}")
    for heading, label, details in (("Günlük", "Günlük", "Günlük ayrıntıları"), ("Kararlar", "Karar", "Karar ayrıntıları")):
        long_lines = [
            line.split(":", 1)[0][2:].strip()[:20] for line in _section(text, heading).splitlines()
            if line.startswith("- ") and len(line.split()) - 1 > 50
        ]
        if long_lines:
            uyarilar.append(
                f".waypoint/ILERLEME.md: {label} satırı 50 kelimeden uzun ({', '.join(long_lines)}); satırı kısa bir özete "
                f"indirin, ayrıntıyı .waypoint/ILERLEME_ARSIV.md dosyasının '## {details}' bölümüne taşıyın."
            )
    # Satır sayısı sınırın altında kalsa da uzun kararlar dosyayı şişirir (gerçek bir projede 20 karar 1.000 kelimeydi).
    decision_words = sum(
        len(line.split()) for line in _section(text, "Kararlar").splitlines() if line.startswith("- ") and "YYYY" not in line
    )
    if decision_words > 600:
        uyarilar.append(
            f".waypoint/ILERLEME.md: Kararlar bölümü {decision_words} kelime (en fazla 600); şu anki işi etkilemeyen en eski "
            "kararları .waypoint/ILERLEME_ARSIV.md dosyasının '## Kararlar' bölümüne taşıyın (arşivdeki kararlar geçerliliğini korur)."
        )
    return hatalar, uyarilar


def fikirler(ilerleme_text: str, fikirler_text: str | None) -> tuple[list[str], list[str]]:
    """'Sonra yapılacaklar' yer tutucuları ile FIKIRLER.md başlıklarını eşleştirir."""
    parked = _without_html_comments(_section(ilerleme_text, "Sonra yapılacaklar"))
    refs = {name.strip() for name in re.findall(r"FIKIRLER\.md\s*[›>]\s*(.+?)\s*$", parked, flags=re.MULTILINE)}
    sections = set() if fikirler_text is None else {
        line[3:].strip() for line in _without_html_comments(fikirler_text).splitlines() if line.startswith("## ")
    }
    hatalar = [
        f".waypoint/FIKIRLER.md: '{name}' için ayrıntı başlığı yok; '## {name}' başlığını ekleyin veya ILERLEME.md'deki yer tutucuyu düzeltin."
        for name in sorted(refs - sections)
    ]
    hatalar += [
        f".waypoint/FIKIRLER.md: '## {name}' bölümü 'Sonra yapılacaklar'da yok; fikir yapıldıysa veya vazgeçildiyse bu bölümü silin."
        for name in sorted(sections - refs)
    ]
    return hatalar, []


_WAYPOINT_FILES = {
    "KURALLAR.md", "ILERLEME.md", "ILERLEME_ARSIV.md", "DERSLER.md", "DERS_ARSIV.md",
    "HARITA.md", "FIKIRLER.md", "WAYPOINT_GUNLUGU.md", "VERSION", ".gitattributes", ".gitignore",
    "guncelle.bat", "guncelle.command",
}


def waypoint_duzeni(staged_names: list[str]) -> tuple[list[str], list[str]]:
    """.waypoint/ içine yalnız Waypoint dosyalarının ve tarihli raporların girmesini sağlar."""
    hatalar: list[str] = []
    for name in staged_names:
        parts = name.replace("\\", "/").split("/")
        if parts[0] != ".waypoint" or len(parts) < 2 or parts[1] == "hooks":
            continue
        if len(parts) == 2 and parts[1] in _WAYPOINT_FILES:
            continue
        if len(parts) == 3 and parts[1] == "komutlar" and parts[2].endswith(".md"):  # Waypoint'in komut tarifleri
            continue
        if parts[1] == "raporlar" and len(parts) >= 3:
            if re.match(r"^\d{4}-\d{2}-\d{2}-.+", parts[2]) and (len(parts) > 3 or parts[2].endswith(".md")):
                continue
            hatalar.append(
                f"{name}: rapor adı tarihle başlamalı. Tek dosya için .waypoint/raporlar/YYYY-AA-GG-<konu>.md, "
                "çok dosya için .waypoint/raporlar/YYYY-AA-GG-<konu>/ klasörünü kullanın."
            )
            continue
        hatalar.append(
            f"{name}: .waypoint/ içinde Waypoint'e ait olmayan dosya. Raporsa .waypoint/raporlar/YYYY-AA-GG-<konu>.md "
            "(çok dosyaysa YYYY-AA-GG-<konu>/ klasörü) olarak taşıyın; değilse proje klasörüne taşıyın."
        )
    return hatalar, []


def _is_code_file(name: str) -> bool:
    normalized = name.replace("\\", "/")
    basename = normalized.rsplit("/", 1)[-1]
    return (
        not normalized.startswith(".waypoint/")
        and not basename.endswith(".md")
        and basename not in {".gitignore", ".gitattributes"}
    )


def _is_test_file(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return _is_code_file(name) and bool(
        re.search(r"test|spec", normalized.rsplit("/", 1)[-1], re.IGNORECASE)
        or re.search(r"(^|/)(tests?|__tests__|specs?)/", normalized, re.IGNORECASE)
    )


def kayit_turu(message_text: str, staged_names: list[str], test_komutu_var: bool) -> tuple[list[str], list[str]]:
    lines = [line for line in message_text.splitlines() if line.strip() and not line.startswith("#")]
    if not lines:
        return ["Kayıt mesajı İngilizce olmalı ve Conventional Commits biçiminde başlamalı: 'feat:', 'fix:', 'docs:', 'refactor:', 'test:', 'chore:', 'style:' veya 'perf:'. Örnek: 'feat: add login button', 'fix: prevent empty tasks'"], []
    subject = lines[0]
    if subject.startswith(("Merge ", 'Revert "', "fixup!", "squash!")):
        return [], []
    match = re.match(r"^(feat|fix|docs|refactor|test|chore|style|perf)(?:\([\w./-]+\))?!?: (\S.*)", subject)
    if not match:
        return ["Kayıt mesajı İngilizce olmalı ve Conventional Commits biçiminde başlamalı: 'feat:', 'fix:', 'docs:', 'refactor:', 'test:', 'chore:', 'style:' veya 'perf:'. Örnek: 'feat: add login button', 'fix: prevent empty tasks'"], []
    kind = match.group(1)
    code_names = [name for name in staged_names if _is_code_file(name)]
    description = match.group(2)
    if any(char in description for char in "ğĞışŞİ"):
        return ["Kayıt mesajı İngilizce olmalı; Türkçe açıklamayı İngilizceye çevirin."], []
    test_names = [name for name in code_names if _is_test_file(name)]
    if kind == "docs" and code_names:
        return ["'docs:' türü yalnız .waypoint/ ve .md dosyaları içindir; türü düzeltin ya da kod değişikliğini ayrı kayda alın."], []
    if kind == "test" and any(not _is_test_file(name) for name in code_names):
        return ["'test:' türü yalnız test dosyaları içindir; diğer kod değişikliklerini ayrı kayda alın."], []
    if (kind == "fix" and test_komutu_var and code_names
            and not test_names
            and "no test:" not in message_text.lower() and "test yok:" not in message_text.lower()):
        return ["'fix:' kaydında bu hatayı yakalayan bir test olmalı. Test ekleyin; test yazılamıyorsa mesaja '(no test: <reason>)' ekleyin."], []
    return [], []


def _not_mu(name: str) -> bool:
    normalized = name.replace("\\", "/")
    if normalized.startswith(".waypoint/"):
        return not normalized.startswith(".waypoint/hooks/")
    lower = normalized.lower()
    return lower.endswith(".md") and ("/" not in lower or lower.startswith("docs/"))


def sadece_notlar(names: list[str]) -> bool:
    """Testleri etkilemeyen notlar: Waypoint defterleri (hook'lar hariç), kökteki ve docs/ altındaki .md dosyaları.
    Kodun okuyabileceği başka .md'ler (ör. src/prompts/) ve emin olunamayan her şey testleri çalıştırır."""
    return bool(names) and all(_not_mu(name) for name in names)


_TESTSIZ_SATIRI = re.compile(r"^(?:[-*+]\s+)?testsiz:(.*)$", re.IGNORECASE | re.MULTILINE)


def testsiz_klasorler(ilerleme_text: str) -> list[str]:
    """'Testleri çalıştırma' altındaki 'Testsiz: docs/taslak/, site/' satırı: testlerin denemediği klasörler.
    Projenin tamamını, Waypoint'in kendisini ya da depo dışını gösteren yollar yok sayılır."""
    match = _TESTSIZ_SATIRI.search(_section(ilerleme_text, "Testleri çalıştırma"))
    folders = []
    # Parantez içi açıklama ("site/ (tasarım taslağı)") klasör sayılmaz.
    for raw in re.split(r"[,\s]+", re.sub(r"\([^)]*\)", " ", match.group(1)) if match else ""):
        path = raw.strip("`'\"").replace("\\", "/").strip("/")
        if not path or path.startswith((".", "/")) or ".." in path.split("/") or "*" in path or ":" in path:
            continue
        folders.append(path + "/")
    return folders


def testsiz_degisiklik(names: list[str], folders: list[str]) -> bool:
    """Değişen her dosya ya not ya da testsiz bir klasörde, ve en az biri testsiz klasörde."""
    def testsiz(name: str) -> bool:
        return any(name.replace("\\", "/").startswith(folder) for folder in folders)
    return any(testsiz(name) for name in names) and all(_not_mu(name) or testsiz(name) for name in names)


def test_komutu(ilerleme_text: str) -> bool:
    section = _section(ilerleme_text, "Testleri çalıştırma")
    return any(command.strip() not in {"...", "…"} for command in re.findall(r"`([^`]+)`", section))


def test_komutunu_bul(ilerleme_text: str) -> str | None:
    """'Testleri çalıştırma' altındaki ilk `komut`; yoksa ya da hâlâ '...' ise None."""
    match = re.search(r"`([^`\n]+)`", _section(ilerleme_text, "Testleri çalıştırma"))
    command = match.group(1).strip() if match else ""
    return None if command in {"", "...", "…"} else command


def test_komutu_uyarisi(ilerleme_text: str, staged_names: list[str]) -> list[str]:
    """Kod değişti ama test komutu yoksa testler hiç çalışmaz; bu sessizce geçmesin."""
    if test_komutunu_bul(ilerleme_text) is not None or not any(_is_code_file(name) for name in staged_names):
        return []
    return [
        "Testler çalışmadı: .waypoint/ILERLEME.md › 'Testleri çalıştırma' altında test komutu yok. Önemli özellikler "
        "için test yazın ve komutu oraya ekleyin; o zamana kadar bozulan eski özellikler kayıtta yakalanmaz."
    ]


TEST_SURESI = 300  # saniye; ILERLEME.md'deki "Süre: 10 dk" satırı ya da WAYPOINT_TEST_TIMEOUT ile değişir
TEST_SURESI_EN_FAZLA = 1800  # takılan bir test kaydı sonsuza kadar bekletmesin
_SURE_SATIRI = re.compile(r"^(?:[-*+]\s+)?süre:\s*(\d+)\s*(dk|dakika|sn|saniye)\s*$", re.IGNORECASE | re.MULTILINE)


def test_suresi(ilerleme_text: str) -> float | None:
    """'Testleri çalıştırma' altındaki 'Süre: 10 dk' satırı (saniye, en fazla 30 dk); yoksa None."""
    match = _SURE_SATIRI.search(_section(ilerleme_text, "Testleri çalıştırma"))
    if not match or int(match.group(1)) == 0:
        return None
    seconds = int(match.group(1)) * (60 if match.group(2).lower() in ("dk", "dakika") else 1)
    return float(min(seconds, TEST_SURESI_EN_FAZLA))


def _sure_yazisi(seconds: float) -> str:
    return f"{seconds / 60:g} dk" if seconds >= 60 else f"{seconds:g} sn"

# Git, hook'a kaydı alınan deponun yerini bu ayarlarla verir (`git rev-parse --local-env-vars`).
# Testlere geçerse, testlerin geçici depolarda çalıştırdığı git komutları gerçek depoyu değiştirir.
_GIT_DEPO_AYARLARI = frozenset({
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT",
    "GIT_OBJECT_DIRECTORY", "GIT_DIR", "GIT_WORK_TREE", "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE",
    "GIT_INDEX_FILE", "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE", "GIT_PREFIX", "GIT_SHALLOW_FILE",
    "GIT_COMMON_DIR", "GIT_NAMESPACE",
})


def _sureci_kapat(process: subprocess.Popen) -> None:
    """Test komutunu, başlattığı alt süreçlerle (node, python…) birlikte kapatır."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, timeout=30)
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        process.kill()
        process.wait(timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass


def _git_exec_path() -> str | None:
    try:
        return subprocess.run(["git", "--exec-path"], capture_output=True, text=True, check=True).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def kabuk_bul(which=shutil.which, git_exec_path=_git_exec_path, windows: bool = os.name == "nt") -> str | None:
    """Test komutunu çalıştıracak 'sh'. Windows'ta PATH'te olmayabilir (git hook'ların dışında);
    o zaman Git for Windows'un kendi kabuğu aranır: <Git>/mingw64/libexec/git-core → <Git>/usr/bin/sh.exe."""
    found = which("sh")
    if found:
        return found
    if windows:
        exec_path = git_exec_path()
        if exec_path:
            candidate = Path(exec_path).parents[2] / "usr" / "bin" / "sh.exe"
            if candidate.is_file():
                return str(candidate)
    return None


# Windows'ta bazı güvenlik kutuları (ör. DeepSeek Harness) Git'in 'sh' programının açılmasını engeller; python ve cmd açılır.
_KABUK_KUTU_IZLERI = ("NtCreateDirectoryObject", "couldn't create signal pipe")
_KABUK_BASLAMADI = (-1073741502, 3221225794)  # 0xC0000142: program daha başlarken durdu


def kabuk_engellendi(returncode: int, text: str) -> bool:
    """Boş bir 'sh -c "exit 0"' denemesinin sonucundan: 'sh'nin kendisi başlayamadıysa True."""
    return returncode != 0 and (returncode in _KABUK_BASLAMADI or any(iz in text for iz in _KABUK_KUTU_IZLERI))


def _sh_engelli(windows: bool = os.name == "nt") -> bool:
    shell = kabuk_bul()
    if not windows or shell is None:
        return False
    try:
        result = subprocess.run([shell, "-c", "exit 0"], capture_output=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return kabuk_engellendi(result.returncode, f"{result.stdout}{result.stderr}")


def _komutu_calistir(command, root: Path, env: dict, timeout: float) -> tuple[int | None, str]:
    """(çıkış kodu, çıktı) döndürür; süre dolduysa çıkış kodu None."""
    group = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    with tempfile.TemporaryFile() as output:  # boru değil dosya: kapanmayan alt süreç beklemeyi kilitlemesin
        process = subprocess.Popen(command, cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT, **group)
        try:
            process.wait(timeout=timeout)
            returncode = process.returncode
        except subprocess.TimeoutExpired:
            _sureci_kapat(process)
            returncode = None
        output.seek(0)
        return returncode, output.read().decode("utf-8", errors="replace")


def testleri_calistir(root: Path, command: str, timeout: float, shell: str | None = None, yedek=None,
                      engelli=_sh_engelli) -> tuple[list[str], str]:
    """Test komutunu süre sınırıyla çalıştırır; (hatalar, çıktı) döndürür. yedek: 'sh' açılamazsa çalışacak komut (testler için)."""
    shell = shell or kabuk_bul()
    if shell is None:
        return [
            f"Testler çalıştırılamadı, kayıt engellendi: 'sh' bulunamadı. Komut: {command}. Waypoint test komutunu Git'in "
            "kabuğuyla çalıştırır; Git'i kurun (Windows: https://git-scm.com/download/win) ve kaydı git ile yapın."
        ], ""
    env = {name: value for name, value in os.environ.items() if name not in _GIT_DEPO_AYARLARI}
    env.setdefault("CI", "true")  # izleme modunda açılan test araçları (vitest, jest) bir kez çalışıp kapansın
    returncode, text = _komutu_calistir([shell, "-c", command], root, env, timeout)
    if returncode not in (None, 0) and engelli():
        # Testler değil kabuk başlayamadı (güvenlik kutusu): aynı komut Windows'un kendi kabuğuyla çalışır.
        # cmd tek tırnağı ve $ işaretini 'sh' gibi okumaz; kalan bir test geçti sanılmasın diye bunlar çalıştırılmaz.
        if yedek is None and any(mark in command for mark in "'$`"):
            return [
                f"Testler bu ortamda çalıştırılamadı, kayıt engellendi: 'sh' açılamıyor ve komut 'sh' söz dizimi kullanıyor. Komut: "
                f"{command}. ILERLEME.md › 'Testleri çalıştırma' altındaki komutta tek tırnak ve $ yerine çift tırnak kullanın."
            ], text
        returncode, text = _komutu_calistir(yedek or f'cmd /d /s /c "{command}"', root, env, timeout)
        text = f"('sh' bu ortamda açılamadı; testler cmd ile çalıştırıldı.)\n{text}"
    if returncode is None:
        minutes = f"{timeout / 60:g} dakikada" if timeout >= 60 else f"{timeout:g} saniyede"
        return [
            f"Testler {minutes} bitmedi, kayıt engellendi. Komut: {command}. Test komutu kendiliğinden kapanmıyor olabilir "
            "(izleme modu); ILERLEME.md'deki komutu bir kez çalışıp kapanacak hale getirin (örn. 'vitest run'). Testler "
            "gerçekten bu kadar uzun sürüyorsa ILERLEME.md › 'Testleri çalıştırma' altına 'Süre: 10 dk' satırını ekleyin "
            "ya da sayıyı artırın (en fazla 30 dk)."
        ], text
    if returncode != 0:
        return [f"Testler geçmedi, kayıt engellendi. Komut: {command}"], text
    return [], text


def ilerleme_bugun(ilerleme_text: str, today: str, staged_names: list[str]) -> tuple[list[str], list[str]]:
    if any(_is_code_file(name) for name in staged_names):
        daily = _section(ilerleme_text, "Günlük")
        if not any(line.startswith(f"- {today}") for line in daily.splitlines()):
            return [
                f".waypoint/ILERLEME.md: kod değişti ama Günlük bölümünde bugünün ({today}) satırı yok; '- {today}: ne yapıldı' satırını ekleyip aynı kayda dahil edin."
            ], []
    return [], []


_BOS_YAKALAMA_TEK = re.compile(r"\bcatch\s*(\([^)]*\))?\s*\{\s*\}|^\s*except\b[^:]*:\s*(pass|\.\.\.)\s*$")
_YAKALAMA_BASI = re.compile(r"\bcatch\s*(\([^)]*\))?\s*\{\s*$|^\s*except\b[^:]*:\s*(#.*)?$")
_BOS_GOVDE = re.compile(r"^\s*(\}|pass|\.\.\.)\s*$")


def yutulan_hatalar(diff_text: str) -> tuple[list[str], list[str]]:
    """Eklenen satırlarda içi boş hata yakalama bloğu (except: pass, catch {}) olan dosyalar için tek bir uyarı verir."""
    files: list[str] = []
    current = None
    previous = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            current = target[2:] if target.startswith("b/") else None
            previous = None
            continue
        if not current or not line.startswith("+"):
            previous = None
            continue
        code = line[1:]
        empty = bool(_BOS_YAKALAMA_TEK.search(code)) or (
            previous is not None and _YAKALAMA_BASI.search(previous) is not None and _BOS_GOVDE.match(code) is not None
        )
        if empty and current not in files:
            files.append(current)
        previous = code
    if not files:
        return [], []
    return [], [
        f"Hata sessizce yutuluyor olabilir (içi boş except/catch): {', '.join(files)}. Hatayı kullanıcıya sade bir mesajla "
        "gösterin ya da günlüğe yazın; bilerek boş bırakıldıysa nedenini yanına yorum olarak yazın."
    ]


# Dosyalar arası bağlantılar (JS/HTML/CSS): taşınan ya da bölünen bir dosya projeyi sessizce bozmasın.
# Yalnız uzantılı göreli yollar denetlenir ('./a.js', '../b/c.css', HTML'de 'stil.css'); paket adları, kök yolları ('/src/x'),
# uzantısız yollar (derleyici çözer) ve çalışırken kurulan yollar ('${...}') atlanır: yanlış engel, engelsizlikten kötü.
BAGLANTI_UZANTILARI = {".js", ".mjs", ".html", ".htm", ".css"}
_JS_FROM = re.compile(r"""\b(?:import|export)\s+([^'";]*?)\s*from\s*(['"])([^'"\n]+)\2""", re.S)
_JS_YAN_ETKI = re.compile(r"""\bimport\s*(['"])([^'"\n]+)\1""")
_JS_DINAMIK = re.compile(r"""\bimport\(\s*(['"])([^'"\n]+)\1\s*\)""")
_JS_URL = re.compile(r"""\bnew\s+URL\(\s*(['"])([^'"\n]+)\1\s*,\s*import\.meta\.url""")
_HTML_YOL = re.compile(r"""<(?:script|link|img|source|iframe)\b[^>]*?\b(?:src|href)\s*=\s*(['"])([^'"]+)\1""", re.I)
_CSS_YOL = re.compile(r"""(?:url\(\s*(['"]?)([^'")]+)\1\s*\)|@import\s+(['"])([^'"]+)\3)""")
_EXPORT_AD = re.compile(r"""\bexport\s+(?:default\s+)?(?:async\s+)?(?:function\*?|const|let|var|class)\s+([A-Za-z_$][\w$]*)""")
_EXPORT_LISTE = re.compile(r"""\bexport\s*\{([^}]*)\}""")
_JS_YORUM = re.compile(r"""/\*.*?\*/|(?<![:'"\\\w])//[^\n]*""", re.S)
_HTML_YORUM = re.compile(r"<!--.*?-->", re.S)


def _denetlenecek_yol(yol: str, js: bool) -> bool:
    """JS'te './' ya da '../' ile başlamayan yol paket adıdır; HTML/CSS'te 'a.css' de sayfaya göre görelidir."""
    if any(isaret in yol for isaret in ("${", "{{", "{%", "<", "\\")):
        return False
    if js and not yol.startswith(("./", "../")):
        return False
    if yol.startswith(("/", "#", "?")) or re.match(r"^[A-Za-z][\w+.-]*:", yol):
        return False  # kök yolu (sunucuya göre değişir) ya da adres (http:, data:, mailto:)
    return bool(Path(yol.split("?")[0].split("#")[0]).suffix)


def _yolu_coz(kaynak: str, yol: str) -> str | None:
    parcalar = kaynak.split("/")[:-1]
    for parca in yol.split("?")[0].split("#")[0].split("/"):
        if parca in ("", "."):
            continue
        if parca == "..":
            if not parcalar:
                return None  # proje klasörünün dışı: denetlenmez
            parcalar.pop()
        else:
            parcalar.append(parca)
    return "/".join(parcalar)


def _export_adlari(metin: str) -> set[str] | None:
    """Dosyanın dışa verdiği adlar; 'export * from' varsa hepsi bilinemez (None)."""
    metin = _JS_YORUM.sub("", metin)
    if re.search(r"\bexport\s*\*", metin):
        return None
    adlar = set(_EXPORT_AD.findall(metin))
    for liste in _EXPORT_LISTE.findall(metin):
        for parca in liste.split(","):
            if parca.strip():
                adlar.add(parca.strip().split(" as ")[-1].strip())
    if re.search(r"\bexport\s+default\b", metin):
        adlar.add("default")
    return adlar


def kirik_baglantilar(names: list[str], read_file, exists) -> tuple[list[str], list[str]]:
    """names: kayda girecek tüm dosyalar. Her JS/HTML/CSS dosyasındaki göreli yolun var olduğunu ve
    `import { a } from './x.js'` içindeki her adın x.js'te gerçekten dışa verildiğini doğrular."""
    hatalar: list[str] = []
    export_onbellek: dict[str, set[str] | None] = {}
    for name in names:
        tur = Path(name).suffix.lower()
        if tur not in BAGLANTI_UZANTILARI:
            continue
        metin = read_file(name)
        if metin is None or len(metin) > 1_000_000:
            continue
        istekler: list[tuple[str, list[str]]] = []
        if tur in {".js", ".mjs"}:
            temiz = _JS_YORUM.sub("", metin)
            for bas, _, yol in _JS_FROM.findall(temiz):
                ayraclar = re.search(r"\{([^}]*)\}", bas)
                adlar = [p.strip().split(" as ")[0].strip() for p in ayraclar.group(1).split(",")] if ayraclar else []
                istekler.append((yol, [ad for ad in adlar if ad and not ad.startswith("type ")]))
            istekler += [(yol, []) for regex in (_JS_YAN_ETKI, _JS_DINAMIK, _JS_URL) for _, yol in regex.findall(temiz)]
        elif tur == ".css":
            istekler += [(a or b, []) for _, a, _, b in _CSS_YOL.findall(_JS_YORUM.sub("", metin))]
        else:
            istekler += [(yol, []) for _, yol in _HTML_YOL.findall(_HTML_YORUM.sub("", metin))]
        for yol, adlar in istekler:
            yol = yol.strip()
            if not _denetlenecek_yol(yol, tur in {".js", ".mjs"}):
                continue
            hedef = _yolu_coz(name, yol)
            if hedef is None:
                continue
            if not exists(hedef):
                hatalar.append(f"Kırık bağlantı: {name} içindeki '{yol}' yok ({hedef}). Dosya taşındı ya da adı "
                               "değiştiyse yolu düzeltin.")
                continue
            if adlar and Path(hedef).suffix.lower() in {".js", ".mjs"}:
                if hedef not in export_onbellek:
                    hedef_metin = read_file(hedef)
                    export_onbellek[hedef] = _export_adlari(hedef_metin) if hedef_metin is not None else None
                var = export_onbellek[hedef]
                eksik = [ad for ad in adlar if var is not None and ad not in var]
                if eksik:
                    hatalar.append(f"Kırık bağlantı: {name}, {hedef} dosyasından {', '.join(eksik)} istiyor ama orada "
                                   "böyle bir export yok. Kod taşındıysa export'u ya da import'u düzeltin.")
    return list(dict.fromkeys(hatalar)), []  # aynı yol iki kez (import ve yeniden export) tek hata


# Uzun dosya uyarısı: yalnız bu kayıtta sınırı geçen (ya da yeni ve sınırın üstünde olan) kaynak dosyalar için.
DOSYA_SATIR_SINIRI = 400
KAYNAK_UZANTILARI = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".vue", ".svelte", ".go", ".rs", ".java",
                     ".kt", ".cs", ".rb", ".php", ".swift", ".dart", ".c", ".cc", ".cpp", ".h", ".hpp", ".ps1", ".sh"}


def uzun_dosyalar(boyutlar: list[tuple[str, int | None, int]]) -> tuple[list[str], list[str]]:
    """boyutlar: (dosya, önceki satır sayısı ya da yeni dosyaysa None, kayda girecek satır sayısı)."""
    gecen = [
        f"{name} ({yeni})" for name, eski, yeni in boyutlar
        if Path(name).suffix.lower() in KAYNAK_UZANTILARI and not _is_test_file(name)
        and yeni > DOSYA_SATIR_SINIRI and (eski is None or eski <= DOSYA_SATIR_SINIRI)
    ]
    if not gecen:
        return [], []
    return [], [
        f"Dosya {DOSYA_SATIR_SINIRI} satırı geçti: {', '.join(gecen)}. Birden fazla iş yapıyorsa işine göre bölmeyi ayrı bir "
        "adım olarak önerin (komutlar/kod-degisikligi.md)."
    ]


def _git_output(root: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=root, check=True, capture_output=True, encoding="utf-8", errors="replace",
    )
    return result.stdout.splitlines()


def _git_bytes(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=root, check=True, capture_output=True,
    )
    return result.stdout


def _oku(root: Path, relative: str) -> str | None:
    path = root / relative
    try:
        return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else None
    except OSError:
        return None


def _kayittaki(root: Path, relative: str) -> str | None:
    """Dosyanın kayda girecek (stage edilmiş) hali; git'te hiç yoksa diskteki hali."""
    try:
        return _git_bytes(root, "show", f":{relative}").decode("utf-8", errors="ignore")
    except (subprocess.CalledProcessError, OSError):
        return _oku(root, relative)


def _harita_kaynagi(root: Path):
    """HARITA denetimi için (read_file, exists): kayda girecek dosyalar ve içerikleri. Git'in yok saydığı
    yollar (ör. derlenmiş 'dist/') hiç kayda girmediği için diskte aranır; git okunamazsa her şey diskten."""
    disk = (lambda path: _oku(root, path)), (lambda path: (root / path).exists())
    try:
        tracked = set(_git_bytes(root, "ls-files", "-z").decode("utf-8", errors="replace").split("\0")) - {""}
        changed = set(_git_output(root, "diff", "--name-only", "--no-renames"))  # diskteki hali kayıttakinden farklı
    except (subprocess.CalledProcessError, OSError):
        return disk
    folders = {name.rsplit("/", i)[0] for name in tracked for i in range(1, name.count("/") + 1)}

    def normal(path: str) -> str:
        return path.replace("\\", "/").removeprefix("./").rstrip("/")

    def ignored(path: str) -> bool:
        try:
            return subprocess.run(["git", "check-ignore", "-q", "--", path], cwd=root, capture_output=True).returncode == 0
        except OSError:
            return False

    def exists(path: str) -> bool:
        p = normal(path)
        if p in tracked or p in folders:
            return True
        return disk[1](path) and ignored(p)

    def read_file(path: str) -> str | None:
        p = normal(path)
        if p in tracked:
            return _kayittaki(root, p) if p in changed else _oku(root, p)  # aynıysa diskten: git çağrısı yavaş
        return disk[0](path) if disk[1](path) and ignored(p) else None

    return read_file, exists


def kayda_girmeyenler(root: Path) -> list[str]:
    """Kayda eklenmemiş değişikliği olan, takip edilen ve testleri etkileyebilen dosyalar. Testler diskteki
    dosyalarla çalışır; bunlar varken test sonucu kayda girecek sürümü kanıtlamaz."""
    try:
        names = _git_output(root, "diff", "--name-only", "--no-renames")
    except (subprocess.CalledProcessError, OSError):
        return []
    return [name for name in names if not sadece_notlar([name])]


WAYPOINT_REPO = "1eren0/WaypointSkill"


def _surum(text: str) -> tuple[int, ...]:
    """'1.10' -> (1, 10); sürüm yoksa boş."""
    return tuple(int(part) for part in re.findall(r"\d+", text or "")[:3])


WAYPOINT_RAW = f"https://raw.githubusercontent.com/{WAYPOINT_REPO}/main"


def _github_surumu() -> str:
    import http.client
    import urllib.request

    try:
        with urllib.request.urlopen(f"{WAYPOINT_RAW}/template/.waypoint/VERSION", timeout=5) as response:
            return response.read(100).decode("utf-8", errors="replace")
    except (OSError, ValueError, http.client.HTTPException):
        # Gizli repo: GitHub CLI girişiyle dene (gh yoksa ya da giriş yoksa hata yükselir, yarın tekrar denenir)
        return subprocess.run(
            ["gh", "api", f"repos/{WAYPOINT_REPO}/contents/template/.waypoint/VERSION", "-H", "Accept: application/vnd.github.raw"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=5, check=True,
        ).stdout


def surum_kontrolu(root: Path, today: str, fetch) -> str | None:
    """Günde en fazla bir kez en yeni Waypoint sürümüne bakar; daha yeniyse yapay zekâya mesaj döndürür. Kendisi kurmaz."""
    import http.client

    local = (_oku(root, ".waypoint/VERSION") or "").strip()
    if not _surum(local):
        return None
    cache = root / ".waypoint/.son-surum"
    cached = (_oku(root, ".waypoint/.son-surum") or "").split()
    if len(cached) == 2 and cached[0] == today:
        latest = cached[1]
    else:
        try:
            latest = fetch().strip() or "-"
        except (subprocess.SubprocessError, OSError, ValueError, http.client.HTTPException):
            latest = "-"  # internet yok: yarın tekrar denenir
        try:
            cache.write_text(f"{today} {latest}\n", encoding="utf-8")
        except OSError:
            pass
    if _surum(latest) > _surum(local):
        return (
            f"Waypoint güncellemesi var: {local} → {latest}. Kullanıcıya yenilikleri (CHANGELOG.md) sade Türkçe özetleyin "
            "ve kurmak isteyip istemediğini sorun; kendiliğinden kurmayın."
        )
    return None


def _dolu_satirlar(section: str) -> list[str]:
    """Bölümün yer tutucu olmayan satırları (şablondaki '...', 'YYYY', '(...)' açıklamaları atlanır)."""
    return [
        line.rstrip() for line in _without_html_comments(section).splitlines()
        if line.strip() and "YYYY" not in line and not (line.startswith("(") and line.rstrip().endswith(")"))
        and not _YER_TUTUCU.fullmatch(line.strip())
    ]


# '...', '- ...', '- [ ] 1. ... — bitti sayılır: ...' gibi şablon satırları
_YER_TUTUCU = re.compile(r"[-\s\[\]xX\d.:—…]*(bitti sayılır:)?[-\s.…]*")


def _kisalt(lines: list[str], heading: str, max_lines: int = 6, max_words: int = 60) -> list[str]:
    """Özet kısa kalsın: uzun satırlar ve bölümler kesilir, devamının yeri söylenir."""
    shown = [
        " ".join(line.split(" ")[:max_words]) + " …" if len(line.split()) > max_words else line
        for line in lines[:max_lines]
    ]
    if len(lines) > max_lines or any(len(line.split()) > max_words for line in lines[:max_lines]):
        shown.append(f"(kısaltıldı; tamamı: ILERLEME.md › {heading})")
    return shown


def oturum_ozeti(ilerleme_text: str, dersler_text: str, git: dict | None, yeni_surum: str | None) -> str:
    """Oturum başında okunacak kısa özet; ILERLEME.md ve DERSLER.md'nin tamamını okumanın yerine.
    git: {'degisen': [...], 'son_kayitlar': [...], 'dallar': [...]} ya da git deposu yoksa None."""
    out = ["# Oturum özeti (`kontrol.py --ozet`)"]
    goal = _dolu_satirlar(_section(ilerleme_text, "Proje hedefi"))
    if not goal and not _dolu_satirlar(_section(ilerleme_text, "Plan")):
        out.append("ILERLEME.md boş (doldurulmamış form): komutlar/oturum-basi.md adım 4.")
    for heading in ("Proje hedefi", "Aktif sorgulama", "Aşama", "Şu anki görev", "Sıradaki adım"):
        lines = _dolu_satirlar(_section(ilerleme_text, heading))
        if lines:
            # Yarım kalan sorgulama kaldığı yerden sürsün diye kesilmez.
            out += ["", f"## {heading}", *(lines if heading == "Aktif sorgulama" else _kisalt(lines, heading))]
    plan = _dolu_satirlar(_section(ilerleme_text, "Plan"))
    open_tasks = [line for line in plan if line.startswith("- [ ]")]
    done = sum(1 for line in plan if line.startswith(("- [x]", "- [X]")))
    if plan:
        out += ["", f"## Plan ({done} bitti, {len(open_tasks)} kaldı)", *_kisalt(open_tasks, "Plan", max_lines=5, max_words=30)]
    waiting = [line for line in _dolu_satirlar(_section(ilerleme_text, "Sonra yapılacaklar")) if "cevap bekleniyor" in line]
    if waiting:
        out += ["", "## Cevap bekleyen sorular", *waiting]
    days = sorted(
        (line for line in _dolu_satirlar(_section(ilerleme_text, "Günlük")) if re.match(r"- \d{4}-\d{2}-\d{2}", line)),
        reverse=True,
    )
    if days:
        out += ["", "## Günlük (son 3)", *_kisalt(days[:3], "Günlük", max_words=50)]
    rules = _dolu_satirlar(_section(dersler_text, "Kurallar"))
    out += ["", "## Proje kuralları (DERSLER.md)", *(rules or ["(yok)"])]
    out += ["", "## Git"]
    if git is None:
        out.append("Git deposu yok: komutlar/oturum-basi.md adım 3.")
    else:
        changed = git["degisen"]
        days = git.get("son_kayit_gun")
        if changed and days:
            # Gerçek bir projede 149 dosya 7 gün kaydedilmeden kaldı; her oturum bunu yalnız bir sayı olarak gördü.
            out.append(
                f"⚠️ {len(changed)} dosya kaydedilmemiş ve son kayıt {days} gün önce. Kullanıcıya bir satırla söyleyin; "
                "bu işe aitse kaydedin, bir engel yüzünden kaldıysa komutlar/hata.md."
            )
        out.append(f"Kaydedilmemiş değişiklik: {len(changed)} dosya" + (": " + ", ".join(changed[:10]) if changed else ""))
        if len(changed) > 10:
            out[-1] += f" ve {len(changed) - 10} dosya daha"
        out += ["Son kayıtlar:", *(f"  {line}" for line in git["son_kayitlar"])]
        if git["dallar"]:
            out.append("Açık deney/iş dalları: " + ", ".join(git["dallar"]))
    if yeni_surum:
        out += ["", f"⬆️ {yeni_surum}"]
    out += [
        "",
        "Bu özet ILERLEME.md ve DERSLER.md'nin oturum başında okunmasının yerine geçer. Bir ayrıntı gerekince dosyanın "
        "tamamını değil o bölümü arayın; dosyayı düzenlemeden önce yalnız ilgili bölümü okuyun.",
    ]
    return "\n".join(out)


def _git_ozeti(root: Path) -> dict | None:
    try:
        if _git_output(root, "rev-parse", "--is-inside-work-tree") != ["true"]:
            return None
        changed = [line[3:] for line in _git_output(root, "status", "--porcelain") if line.strip()]
        try:
            commits = _git_output(root, "log", "-5", "--format=%h %ad %s", "--date=short")
            last = int(_git_output(root, "log", "-1", "--format=%ct")[0])
            days = int((datetime.now().timestamp() - last) // 86400)
        except (subprocess.CalledProcessError, IndexError, ValueError):
            commits, days = [], None  # henüz hiç kayıt yok
        branches = [
            name for name in _git_output(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/deney", "refs/heads/is")
        ]
    except (subprocess.CalledProcessError, OSError):
        return None
    return {"degisen": changed, "son_kayitlar": commits or ["(henüz kayıt yok)"], "dallar": branches, "son_kayit_gun": days}


_ATLANAN_KLASORLER = frozenset({".git", "node_modules", ".venv", "venv", "__pycache__", "target", "dist", "build"})


def _kopya_sayisi(folder: Path, depth: int = 3) -> int:
    """Klasördeki proje kopyaları: içinde '.waypoint/KURALLAR.md' ya da git çalışma kopyası işareti ('.git' dosyası) olan klasörler."""
    count = 0
    stack = [(folder, 0)]
    while stack:
        current, level = stack.pop()
        if (current / ".waypoint" / "KURALLAR.md").is_file() or (current / ".git").is_file():
            count += 1
            continue  # kopyanın içindeki kopyalar ayrıca sayılmaz
        if level >= depth:
            continue
        try:
            children = [child for child in current.iterdir() if child.is_dir() and child.name not in _ATLANAN_KLASORLER]
        except OSError:
            continue
        stack += [(child, level + 1) for child in children]
    return count


def _temizlik_bulgulari(root: Path) -> dict:
    """bitir'de sorulacaklar: proje içinde kalan kopyalar, git'e kayıtlı çalışma kopyaları, deney/iş dalları."""
    found = {"kopyalar": [], "calisma_kopyalari": [], "dallar": []}
    try:
        ignored = _git_output(root, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory")
        for rel in ignored:
            rel = rel.rstrip("/")
            if not rel or rel.startswith(".waypoint/") or rel.split("/")[-1] in _ATLANAN_KLASORLER or not (root / rel).is_dir():
                continue
            copies = _kopya_sayisi(root / rel)
            if copies:
                found["kopyalar"].append((rel + "/", copies))
        main_path = None
        for line in _git_output(root, "worktree", "list", "--porcelain"):
            if line.startswith("worktree "):
                path = line[len("worktree "):]
                if main_path is None:
                    main_path = path  # ilk satır ana çalışma klasörü
                elif path.startswith(main_path.rstrip("/") + "/"):
                    found["calisma_kopyalari"].append(path[len(main_path.rstrip("/")) + 1:] + " (proje içinde)")
                else:
                    found["calisma_kopyalari"].append(path)
        merged = set(_git_output(root, "branch", "--merged", "HEAD", "--format=%(refname:short)"))
        current = _git_output(root, "branch", "--show-current")
        for line in _git_output(
            root, "for-each-ref", "--format=%(refname:short)\t%(committerdate:short)", "refs/heads/deney", "refs/heads/is"
        ):
            name, _, day = line.partition("\t")
            if name not in current:  # üzerinde çalışılan dal silinemez
                found["dallar"].append((name, day, name in merged))
    except (subprocess.CalledProcessError, OSError):
        pass
    return found


def temizlik_raporu(found: dict) -> str:
    """Bulguları tek mesajda sorulacak kısa bir listeye çevirir; kendisi hiçbir şey silmez."""
    def listed(items: list[str], limit: int = 10) -> list[str]:
        return [f"- {item}" for item in items[:limit]] + ([f"- … ve {len(items) - limit} tane daha"] if len(items) > limit else [])

    out = ["# Temizlik (`kontrol.py --temizlik`): hiçbir şey silinmedi"]
    if found["kopyalar"]:
        out += ["", "## Proje içinde kalan kopyalar (git yok sayıyor; diskte ve OneDrive'da yer kaplar)"]
        out += listed([f"{rel} ({copies} kopya)" for rel, copies in found["kopyalar"]])
    if found["calisma_kopyalari"]:
        out += ["", "## Git'e kayıtlı çalışma kopyaları (silmek: git worktree remove <yol>; kaydedilmemiş iş varsa git reddeder)"]
        out += listed(found["calisma_kopyalari"])
    merged = [f"{name} (son kayıt {day})" for name, day, is_merged in found["dallar"] if is_merged]
    open_ = [f"{name} (son kayıt {day})" for name, day, is_merged in found["dallar"] if not is_merged]
    if merged:
        out += ["", "## Ana dala birleşmiş dallar (silmek güvenli: git branch -d <dal>)"]
        out += listed(merged)
    if open_:
        out += ["", "## Birleşmemiş dallar (içlerinde ana dalda olmayan iş var)"]
        out += listed(open_)
    if len(out) == 1:
        return out[0].replace(": hiçbir şey silinmedi", ": temizlenecek bir şey yok")
    out += [
        "",
        "Kullanıcıya bunları tek mesajda, ne olduklarını sade dille anlatarak sorun ve yalnız onayladıklarını silin. "
        "Birleşmemiş bir dalı ya da içinde kaydedilmemiş iş olan bir kopyayı silmeden önce içinde ne kaldığını söyleyin.",
    ]
    return "\n".join(out)


def _onbellekteki_surum(root: Path) -> str | None:
    """Ağa çıkmadan: günlük sürüm denetiminin bıraktığı '.son-surum' daha yeniyse mesaj."""
    local = (_oku(root, ".waypoint/VERSION") or "").strip()
    cached = (_oku(root, ".waypoint/.son-surum") or "").split()
    if len(cached) == 2 and _surum(local) and _surum(cached[1]) > _surum(local):
        return (
            f"Waypoint güncellemesi var: {local} → {cached[1]}. Kullanıcıya yenilikleri (CHANGELOG.md) sade Türkçe özetleyin "
            "ve kurmak isteyip istemediğini sorun; kendiliğinden kurmayın."
        )
    return None


OTO_KAYIT = ".waypoint/oto-kayit.log"


def oto_kayit(root: Path, durum: str, satirlar: list[str]) -> None:
    """Kontrol sonuçlarını git'e girmeyen yerel bir dosyaya ekler; Waypoint'in işe yarayıp yaramadığını değerlendirmek için."""
    path = root / OTO_KAYIT
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        with path.open("a", encoding="utf-8") as log:
            for satir in satirlar:
                first_line = (satir.strip().splitlines() or [""])[0]
                log.write(f"{stamp}  {durum}  {first_line[:200]}\n")
        if path.stat().st_size > 200_000:  # en yeni yarısı kalsın
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            path.write_text("".join(lines[len(lines) // 2:]), encoding="utf-8")
    except OSError:
        pass


# Her kayıtta tekrarlanınca okunmayan uyarılar: günde bir kez yeter.
_GUNDE_BIR = (".waypoint/HARITA.md eski biçimde",)


def _bugun_soylendi(root: Path, uyari: str) -> bool:
    """Günde bir kez gösterilen bir uyarı bugün oto-kayit.log'a zaten yazıldıysa True."""
    prefix = next((p for p in _GUNDE_BIR if uyari.startswith(p)), None)
    if prefix is None:
        return False
    try:
        log = (root / OTO_KAYIT).read_text(encoding="utf-8")
    except OSError:
        return False
    today = date.today().isoformat()
    return any(line.startswith(today) and f"  UYARI  {prefix}" in line for line in log.splitlines())


# Waypoint'in kendi dosyaları (kurulumdaki $managed ile aynı); kullanıcının notlarına ve raporlarına dokunulmaz.
_YONETILEN = ("KURALLAR.md", "VERSION", ".gitattributes", ".gitignore", "guncelle.bat", "guncelle.command", "hooks", "komutlar")
_GEREKLI = ("KURALLAR.md", "hooks/kontrol.py", "hooks/pre-commit", "komutlar/oturum-basi.md")


class GuncellemeHatasi(Exception):
    pass


def _tam_kurulum(folder: Path, expected: str) -> bool:
    """folder'da beklenen sürüm ve her projenin ihtiyaç duyduğu dosyalar var mı (kurulumdaki Test-Complete)."""
    version = _oku(folder.parent, f"{folder.name}/VERSION")
    if version is None or version.strip() != expected:
        return False
    return all((folder / name).is_file() and (folder / name).stat().st_size > 0 for name in _GEREKLI)


def _sil(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _yedegi_geri_koy(waypoint: Path) -> bool:
    """Değiştirmeden önce saklanan dosyaları yerine koyar; yarıda kalmış bir güncellemeyi de toparlar."""
    backup = waypoint / ".guncelleme-yedek"
    if not backup.exists():
        return True
    try:
        for item in _YONETILEN:
            saved = backup / item
            if saved.exists():
                _sil(waypoint / item)
                saved.replace(waypoint / item)
        shutil.rmtree(backup)
        return True
    except OSError:
        return False


def waypoint_indir(folder: Path) -> Path:
    """En yeni Waypoint'i folder içine indirir ve template klasörünü döndürür. Yalnız dosya indirir, kod çalıştırmaz."""
    if os.environ.get("WAYPOINT_SOURCE"):  # testler: yerel kopya
        return Path(os.environ["WAYPOINT_SOURCE"]) / "template"
    import http.client
    import urllib.request
    import zipfile

    archive = folder / "waypoint.zip"
    try:
        urllib.request.urlretrieve(f"https://github.com/{WAYPOINT_REPO}/archive/refs/heads/main.zip", archive)
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(folder / "acilan")
        return next((folder / "acilan").iterdir()) / "template"
    except (OSError, ValueError, StopIteration, zipfile.BadZipFile, http.client.HTTPException):
        pass
    # Gizli repo: GitHub CLI girişiyle indir
    clone = folder / "kaynak"
    try:
        subprocess.run(["gh", "repo", "clone", WAYPOINT_REPO, str(clone), "--", "--depth", "1", "-q"],
                       capture_output=True, timeout=120, check=True)
    except (subprocess.SubprocessError, OSError):
        raise GuncellemeHatasi(
            "Waypoint indirilemedi. İnternet bağlantısını kontrol edin; repo gizliyse GitHub CLI kurup 'gh auth login' ile "
            "giriş yapın."
        ) from None
    return clone / "template"


def guncelle(root: Path, source: Path) -> str:
    """Kurulu Waypoint'in kendi dosyalarını source'takilerle değiştirir. Yeni dosyalar yanda hazırlanır, adları
    değiştirilerek yerine konur; bir hata ya da Ctrl+C'de eski dosyalar geri gelir. Notlara dokunulmaz."""
    for name in (".waypoint/ILERLEME.md", ".waypoint/DERSLER.md", ".waypoint/HARITA.md",
                 *(f".waypoint/{item}" for item in _GEREKLI), *(f".waypoint/{item}" for item in _YONETILEN)):
        if not (source / name).exists() or ((source / name).is_file() and (source / name).stat().st_size == 0):
            raise GuncellemeHatasi(f"İndirilen Waypoint eksik ({name} yok). Hiçbir şey değiştirilmedi; biraz sonra tekrar deneyin.")
    expected = (_oku(source, ".waypoint/VERSION") or "").strip()
    if not _surum(expected):
        raise GuncellemeHatasi("İndirilen Waypoint bozuk (sürüm yok). Hiçbir şey değiştirilmedi; biraz sonra tekrar deneyin.")
    waypoint = root / ".waypoint"
    if not waypoint.is_dir():
        raise GuncellemeHatasi("Bu projede Waypoint kurulu değil. İlk kurulum için README'deki kurulum komutunu kullanın.")
    old = (_oku(root, ".waypoint/VERSION") or "?").strip()
    new = waypoint / ".guncelleme-yeni"
    backup = waypoint / ".guncelleme-yedek"
    if backup.exists():
        if not _yedegi_geri_koy(waypoint):
            raise GuncellemeHatasi(f"Önceki güncelleme yarıda kalmış ve eski dosyalar geri konamadı. Eski dosyalar {backup} içinde.")
        print("Önceki güncelleme yarıda kalmıştı; eski kurulum geri getirildi, şimdi güncelleniyor.")
    try:
        _sil(new)
        (new / "hooks").mkdir(parents=True)
        for item in _YONETILEN:
            if item == "komutlar":
                shutil.copytree(source / ".waypoint" / item, new / item, ignore=shutil.ignore_patterns("__pycache__"))
            elif item != "hooks":
                shutil.copy2(source / ".waypoint" / item, new / item)
        for hook in (source / ".waypoint/hooks").iterdir():
            if hook.is_file():
                shutil.copy2(hook, new / "hooks" / hook.name)
                if os.name != "nt":  # zip arşivi çalıştırma iznini taşımaz; git izinsiz hook'u çalıştırmaz
                    (new / "hooks" / hook.name).chmod(0o755)
        if not _tam_kurulum(new, expected):
            raise GuncellemeHatasi("Yeni dosyalar hazırlanamadı.")
        backup.mkdir()
        for item in _YONETILEN:
            if (waypoint / item).exists():
                (waypoint / item).replace(backup / item)
        for item in _YONETILEN:
            if os.environ.get("WAYPOINT_TEST_KESINTI") == "1" and item == "hooks":
                raise GuncellemeHatasi("test: yarıda kesildi")
            (new / item).replace(waypoint / item)
        if not _tam_kurulum(waypoint, expected):
            raise GuncellemeHatasi("Yeni sürüm doğrulanamadı.")
    except BaseException as exc:  # Ctrl+C dahil: eski dosyalar geri gelsin
        if not _yedegi_geri_koy(waypoint):
            raise GuncellemeHatasi(f"Güncelleme tamamlanamadı ve eski dosyalar geri konamadı. Eski dosyalar {backup} içinde duruyor.") from exc
        shutil.rmtree(new, ignore_errors=True)
        if isinstance(exc, KeyboardInterrupt):
            raise
        raise GuncellemeHatasi(f"Güncelleme tamamlanamadı; eski kurulum geri getirildi. Notlarınız değişmedi. ({exc})") from exc
    shutil.rmtree(backup, ignore_errors=True)
    shutil.rmtree(new, ignore_errors=True)
    for name in ("ILERLEME.md", "DERSLER.md", "HARITA.md"):
        if not (waypoint / name).exists():
            shutil.copy2(source / ".waypoint" / name, waypoint / name)
    if Path(_hook_yolu(root) or "").name != _PYTHON_HOOK_KLASORU:  # güvenlik kutusu için Python hook'larına geçilmişse öyle kalır
        subprocess.run(["git", "-C", str(root), "config", "core.hooksPath", ".waypoint/hooks"], capture_output=True, check=False)
    return f"Waypoint güncellendi: {old} → {expected}."


def testleri_denetle(root: Path) -> int:
    """Projenin testleri (ILERLEME.md'deki komut); pre-commit'in ikinci adımı."""
    return _testler(root)[0]


def _testler(root: Path) -> tuple[int, bool]:
    """(çıkış kodu, testler gerçekten çalışıp geçti mi)."""
    progress_text = _kayittaki(root, ".waypoint/ILERLEME.md") or ""
    command = test_komutunu_bul(progress_text)
    try:
        staged = _git_output(root, "diff", "--cached", "--name-only", "--no-renames")
    except (subprocess.CalledProcessError, OSError):
        staged = []
    if command is None:
        # "Kayıt alındı" test edildi sanılmasın: kod değiştiyse hiçbir testin çalışmadığı açıkça yazılır.
        if any(_is_code_file(name) for name in staged):
            print("⚠️ Bu kayıtta hiçbir test çalışmadı (test komutu yok); kod denenmeden kaydedildi.")
            oto_kayit(root, "TEST", ["yok: test komutu yok, kod denenmeden kaydedildi"])
        return 0, False
    if sadece_notlar(staged):
        print("ℹ️ Sadece notlar değişti; testler atlandı (gizli bilgi ve diğer kontroller yine çalıştı).")
        return 0, False
    untested = testsiz_klasorler(progress_text)
    if testsiz_degisiklik(staged, untested):
        print(
            f"ℹ️ Değişen dosyalar test gerektirmeyen klasörlerde ({', '.join(untested)}; ILERLEME.md › 'Testsiz'); "
            "testler atlandı (gizli bilgi ve diğer kontroller yine çalıştı)."
        )
        oto_kayit(root, "TEST", [f"atlandı: yalnız testsiz klasörler ({', '.join(untested)})"])
        return 0, False
    unstaged = kayda_girmeyenler(root)
    if unstaged:
        shown = ", ".join(unstaged[:5]) + (f" ve {len(unstaged) - 5} dosya daha" if len(unstaged) > 5 else "")
        error = (
            f"Kayda girmeyen değişiklik var: {shown}. Testler diskteki dosyalarla çalışır, kayda girecek sürümü "
            "kanıtlamaz; kayıt engellendi. Bu değişiklikler de bu kayda aitse 'git add' ile ekleyin. Değilse önce "
            "'git stash push --keep-index' ile kenara alın, kaydedin, sonra 'git stash pop' ile geri getirin."
        )
        print(f"❌ {error}")
        oto_kayit(root, "ENGEL", [error])
        return 1, False
    try:
        timeout = float(os.environ.get("WAYPOINT_TEST_TIMEOUT") or test_suresi(progress_text) or TEST_SURESI)
    except ValueError:
        timeout = test_suresi(progress_text) or TEST_SURESI
    # Yapay zekâ beklemesi gerektiğini bilsin; sessiz geçen dakikaları takılma sanmasın.
    print(
        f"⏳ Testler başlıyor (en fazla {_sure_yazisi(timeout)}). Komut: {command}. Kaydın bitmesini tek seferde "
        "bekleyin; arada tekrar tekrar kontrol etmeyin.",
        flush=True,
    )
    tree = _kaydedilecek_agac(root)  # denenen içerik: testler başlamadan önceki hali
    errors, output = testleri_calistir(root, command, timeout)
    _son_testi_yaz(root, tree, command, not errors)
    if not errors:
        print(f"✅ Testler geçti. Komut: {command}")
        oto_kayit(root, "TEST", [f"geçti: {command}"])
        return 0, True
    print(f"❌ {errors[0]}")
    print("\n".join(output.splitlines()[-30:]))
    oto_kayit(root, "ENGEL", errors)
    return 1, False


def _baglanti_denetimi(root: Path, kaynak) -> list[str]:
    """Kayda girecek tüm JS/HTML/CSS dosyalarında kırık bağlantı: değişmeyen bir dosya da taşınan bir dosyayı gösterebilir."""
    read_file, exists = kaynak
    try:
        names = [n for n in _git_output(root, "ls-files") if Path(n).suffix.lower() in BAGLANTI_UZANTILARI
                 and not n.startswith(".waypoint/")]
    except (subprocess.CalledProcessError, OSError):
        return []
    if not names:
        return []

    def var_mi(path: str) -> bool:
        if exists(path):
            return True
        try:  # git'in yok saydığı (ör. derlenip oluşan) bir dosya henüz diskte olmayabilir: engel sebebi değil
            return subprocess.run(["git", "check-ignore", "-q", "--no-index", "--", path], cwd=root,
                                  capture_output=True).returncode == 0
        except OSError:
            return True

    return kirik_baglantilar(names, read_file, var_mi)[0]


def _satir_sayilari(root: Path, staged: list[str]) -> list[tuple[str, int | None, int]]:
    sonuc = []
    for name in staged:
        if Path(name).suffix.lower() not in KAYNAK_UZANTILARI or _is_test_file(name):
            continue
        try:
            yeni = _git_bytes(root, "show", f":{name}").count(b"\n")
        except (subprocess.CalledProcessError, OSError):
            continue
        try:
            eski = _git_bytes(root, "show", f"HEAD:{name}").count(b"\n")
        except (subprocess.CalledProcessError, OSError):
            eski = None
        sonuc.append((name, eski, yeni))
    return sonuc


def kurallari_denetle(root: Path) -> int:
    """Belge, gizli bilgi ve düzen kuralları; pre-commit'in ilk adımı."""
    try:
        staged = _git_output(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"❌ .waypoint/hooks/kontrol.py: Git deposu okunamadı; hook'u depo içinden çalıştırın. ({exc})")
        return 1

    hatalar, uyarilar = gizli_dosyalar(staged)
    hatalar.extend(waypoint_duzeni(staged)[0])
    for name in staged:
        try:
            data = _git_bytes(root, "show", f":{name}")
        except (subprocess.CalledProcessError, OSError):
            continue
        errors, _ = bozuk_dosya(name, data)
        hatalar.extend(errors)
        if Path(name).suffix.lower() not in _BINARY_EXTENSIONS and b"\x00" not in data[:8000]:
            secrets, _ = gizli_icerik(name, data.decode("utf-8", errors="ignore"))
            hatalar.extend(secrets)
    today = date.today().isoformat()
    # Belgeler kayda girecek halleriyle denetlenir: diskte düzeltilip 'git add' edilmemiş satır kontrolü geçirmesin.
    for path, check in ((".waypoint/HARITA.md", harita), (".waypoint/DERSLER.md", dersler), (".waypoint/ILERLEME.md", ilerleme)):
        file_text = _kayittaki(root, path)
        if file_text is not None:
            errors, warnings = check(file_text)
            hatalar.extend(errors)
            uyarilar.extend(warnings)
            if path == ".waypoint/ILERLEME.md":
                errors, warnings = ilerleme_bugun(file_text, today, staged)
                hatalar.extend(errors)
                uyarilar.extend(warnings)
                errors, _ = fikirler(file_text, _kayittaki(root, ".waypoint/FIKIRLER.md"))
                hatalar.extend(errors)
                uyarilar.extend(test_komutu_uyarisi(file_text, staged))
    code_paths = [name for name in staged if _is_code_file(name) and not _is_test_file(name)]
    if code_paths:
        try:
            diff_text = "\n".join(_git_output(root, "diff", "--cached", "-U0", "--diff-filter=ACMR", "--", *code_paths))
            uyarilar.extend(yutulan_hatalar(diff_text)[1])
        except (subprocess.CalledProcessError, OSError):
            pass  # yalnızca bir uyarı
    kaynak = _harita_kaynagi(root)
    map_text = _kayittaki(root, ".waypoint/HARITA.md")
    if map_text is not None:
        errors, _ = harita_gercek(map_text, *kaynak)
        hatalar.extend(errors)
    hatalar.extend(_baglanti_denetimi(root, kaynak))
    uyarilar.extend(uzun_dosyalar(_satir_sayilari(root, staged))[1])
    uyarilar = [uyari for uyari in uyarilar if not _bugun_soylendi(root, uyari)]
    for hata in hatalar:
        print(f"❌ {hata}")
    for uyari in uyarilar:
        print(f"⚠️ {uyari}")
    oto_kayit(root, "UYARI", uyarilar)
    if hatalar:
        oto_kayit(root, "ENGEL", hatalar)
        return 1
    print("✅ .waypoint/hooks/kontrol.py: Belgeler ve gizli dosya denetimleri geçti.")
    return 0


# "Az önce doğrulandı" işareti: `--dogrula` kurallar ve testler geçince git klasörüne (.git/waypoint-verified) kaydedilecek
# ağacın (git write-tree) ve üstüne kaydedileceği HEAD'in kimliğini yazar (denetimler HEAD'e göre farka bakar: aynı ağaç
# başka bir HEAD'in üstünde başka bir değişikliktir). Test komutu yoksa ya da testler atlandıysa işaret yazılmaz. pre-commit (`--kayit-oncesi`) aynı ağaç kaydedilirken ikisini tekrar çalıştırmaz.
# İşaret bir kez kullanılır; ağaç, kontrol.py/VERSION, gün ya da süre tutmazsa ya da okunamazsa denetimlerin hepsi çalışır.
DOGRULAMA_ISARETI = "waypoint-verified"
DOGRULAMA_SURESI = 15 * 60  # saniye


def _dogrulama_imzasi(root: Path) -> str:
    """Denetimleri yapan kodun kimliği: kontrol.py ya da VERSION değişince eski işaret geçmez."""
    digest = hashlib.sha256(Path(__file__).read_bytes())
    digest.update(b"\0" + ((_oku(root, ".waypoint/VERSION") or "").strip()).encode("utf-8"))
    return digest.hexdigest()


def dogrulama_isareti(tree: str, head: str, imza: str, gun: str, zaman: float) -> str:
    return json.dumps({"surum": 1, "agac": tree, "head": head, "imza": imza, "gun": gun, "zaman": int(zaman)}) + "\n"


def isaret_gecerli(text: str, tree: str, head: str, imza: str, gun: str, zaman: float) -> bool:
    """İşaret, şimdi kaydedilecek ağaç ve HEAD için az önce (aynı gün, aynı kontrol koduyla) yapılmış bir doğrulamayı mı gösteriyor?"""
    try:
        data = json.loads(text)
        yas = zaman - int(data["zaman"])
        return (data["surum"] == 1 and bool(tree) and bool(head) and data["agac"] == tree and data["head"] == head
                and data["imza"] == imza and data["gun"] == gun and 0 <= yas <= DOGRULAMA_SURESI)
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def _isaret_yolu(root: Path, name: str = DOGRULAMA_ISARETI) -> Path | None:
    if not os.environ.get("GIT_DIR") and (root / ".git").is_dir():  # olağan depo: git'i başlatmaya gerek yok (Windows'ta yavaş)
        return root / ".git" / name
    try:  # worktree ya da GIT_DIR ile ayrı git klasörü
        return root / _git_output(root, "rev-parse", "--git-path", name)[0]
    except (subprocess.CalledProcessError, OSError, IndexError):
        return None


def _kaydedilecek_agac(root: Path) -> str | None:
    """Index'in (GIT_INDEX_FILE) ağaç kimliği; birleştirme çakışması varsa ya da okunamazsa None."""
    try:
        return (_git_output(root, "write-tree") or [""])[0].strip() or None
    except (subprocess.CalledProcessError, OSError):
        return None


def _head(root: Path) -> str | None:
    """HEAD'in kimliği; henüz hiç kayıt yoksa "yok", okunamazsa None."""
    try:
        result = subprocess.run(["git", "rev-parse", "-q", "--verify", "HEAD^{commit}"], cwd=root, capture_output=True,
                                encoding="utf-8", errors="replace")
    except OSError:
        return None
    if result.returncode != 0:
        return "yok" if not result.stdout.strip() and not result.stderr.strip() else None
    return result.stdout.strip() or None


def _isareti_sil(path: Path | None) -> None:
    if path is not None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def dogrula(root: Path) -> int:
    """Kurallar ve testler (pre-commit'in yaptığının aynısı); ikisi de geçerse bu ağaç için işaret yazar."""
    path = _isaret_yolu(root)
    _isareti_sil(path)  # başarısız bir doğrulamadan eski işaret kalmasın
    tree, head = _kaydedilecek_agac(root), _head(root)
    if kurallari_denetle(root) != 0:
        return 1
    code, tests_ran = _testler(root)
    if code != 0:
        return 1
    if not tests_ran:  # kayıtta "hiçbir test çalışmadı" uyarısı yine görünsün; atlanacak bir test de yok
        print("✅ Doğrulama tamam: kurallar geçti (test çalışmadı; kayıtta denetimler yine yapılır).")
        return 0
    # Denetim sırasında index ya da HEAD değişmediyse
    if path is not None and tree is not None and head is not None and (_kaydedilecek_agac(root), _head(root)) == (tree, head):
        temp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        try:
            temp.write_text(dogrulama_isareti(tree, head, _dogrulama_imzasi(root), date.today().isoformat(), time.time()),
                            encoding="utf-8")
            os.replace(temp, path)
        except OSError:
            _isareti_sil(temp)
    print("✅ Doğrulama tamam: kurallar ve testler geçti.")
    return 0


def kayit_oncesi(root: Path) -> int:
    """pre-commit: bu ağaç az önce `--dogrula` ile doğrulandıysa tekrar etmez; yoksa kurallar, sonra testler."""
    path = _isaret_yolu(root)
    text = None
    if path is not None:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = None
        _isareti_sil(path)  # tek kullanımlık
    if text is not None and isaret_gecerli(text, _kaydedilecek_agac(root) or "", _head(root) or "", _dogrulama_imzasi(root),
                                           date.today().isoformat(), time.time()):
        print("✅ Bu içerik az önce doğrulandı (kurallar ve testler geçti); tekrar çalıştırılmadı.")
        oto_kayit(root, "TEST", ["atlandı: aynı içerik az önce doğrulandı (kurallar ve testler)"])
        return 0
    if kurallari_denetle(root) != 0:
        return 1
    return testleri_denetle(root)


# Son test çalıştırmasının kalıcı kaydı (.git/waypoint-son-test): `--bitti` "testler bu içerikte gerçekten çalıştı mı?"
# sorusunu buradan yanıtlar. "waypoint-verified" işareti kayıtta silinir (tek kullanımlık); bu kayıt kalır ve testler her
# gerçekten çalıştığında (kayıt, --dogrula, --test) denenen ağaçla yenilenir. Atlanan testler yazılmaz: atlandıkları,
# kayıttaki ağaçla şimdiki içeriğin farkından görülür.
SON_TEST = "waypoint-son-test"


def son_test_kaydi(tree: str, command: str, passed: bool, zaman: float) -> str:
    return json.dumps({"surum": 1, "agac": tree, "komut": command, "gecti": passed, "zaman": int(zaman)}) + "\n"


def son_test_oku(text: str | None) -> dict | None:
    try:
        data = json.loads(text or "")
        if data["surum"] == 1 and data["agac"] and isinstance(data["gecti"], bool):
            return {"agac": str(data["agac"]), "komut": str(data["komut"]), "gecti": data["gecti"], "zaman": int(data["zaman"])}
    except (ValueError, TypeError, KeyError):
        pass
    return None


def _son_testi_yaz(root: Path, tree: str | None, command: str, passed: bool) -> None:
    path = _isaret_yolu(root, SON_TEST)
    if path is None:
        return
    if tree is None:  # denenen içerik bilinmiyor: eski bir "geçti" kaydı yeni içeriği kanıtlıyor sanılmasın
        _isareti_sil(path)
        return
    temp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_text(son_test_kaydi(tree, command, passed, time.time()), encoding="utf-8")
        os.replace(temp, path)
    except OSError:
        _isareti_sil(temp)


def _liste(names: list[str], limit: int = 8) -> str:
    return ", ".join(names[:limit]) + (f" ve {len(names) - limit} dosya daha" if len(names) > limit else "")


_DOGRULA_KOMUTU = "her şeyi 'git add' ile ekleyip `python .waypoint/hooks/kontrol.py --dogrula` çalıştırın"


def test_durumu(kayit: dict | None, komut: str | None, degisen: list[str] | None, testsiz: list[str]) -> tuple[bool, list[str]]:
    """1. bölüm: testler şimdiki içerikte gerçekten çalışıp geçti mi? degisen: kayıttaki ağaçtan bu yana değişen takip
    edilen dosyalar (okunamadıysa None). Atlanan ya da hiç çalışmayan test geçti gibi gösterilmez: test komutu yoksa ya da
    yalnız 'Testsiz' klasörler değiştiyse kapı kapanmaz (çıkmaz sokak olmasın) ama satır ⚠️ ile başlar, ✅ ile değil."""
    if komut is None:
        return True, [
            "⚠️ TEST YOK: test komutu yok (ILERLEME.md › 'Testleri çalıştırma'), bu iş hiçbir testle denenmedi. Kullanıcıya "
            "\"test yok\" deyin, \"geçti\" demeyin; önemli özellikler için test yazın (komutlar/testler.md)."
        ]
    if kayit is None or degisen is None:
        return False, [f"❌ Testlerin çalıştığına dair kayıt yok (hiç çalışmadı ya da kayıt okunamadı); {_DOGRULA_KOMUTU}."]
    when = datetime.fromtimestamp(kayit["zaman"]).strftime("%Y-%m-%d %H:%M")
    if kayit["komut"] != komut:
        return False, [
            f"❌ Testler en son başka bir komutla çalıştı ({kayit['komut']}, {when}); şimdiki komut ({komut}) hiç çalışmadı. "
            f"Testlerin bu komutla çalışması için {_DOGRULA_KOMUTU}."
        ]
    if not kayit["gecti"]:
        return False, [f"❌ Testler en son geçmedi ya da çalıştırılamadı (komut: {komut}, {when}). Düzeltin, sonra {_DOGRULA_KOMUTU}."]
    notes = [name for name in degisen if _not_mu(name)]
    relevant = [name for name in degisen if not _not_mu(name)]
    if relevant and testsiz_degisiklik(relevant, testsiz):
        return True, [
            f"⚠️ TESTLER ATLANDI: şimdiki içerikte ÇALIŞMADI. Son geçen testten ({when}) sonra yalnız test gerektirmeyen "
            f"klasörlerde değişiklik var ({', '.join(testsiz)}; ILERLEME.md › 'Testsiz'), bu yüzden kayıtta atlandılar: "
            f"{_liste(relevant)}. Kullanıcıya \"testler atlandı, çünkü …\" deyin, \"geçti\" demeyin."
        ]
    if relevant:
        return False, [
            f"❌ Testler {when}'de geçti ama içerik o zamandan beri değişti: {_liste(relevant)}. Bu hali denenmedi; {_DOGRULA_KOMUTU}."
        ]
    line = f"✅ Testler bu içerikte geçti (komut: {komut}, {when})."
    if notes:
        line += f" Sonra yalnız notlar değişti (testleri etkilemez): {_liste(notes, 5)}."
    return True, [line]


def kayit_durumu(info: dict | None) -> tuple[bool, list[str]]:
    """2. bölüm: iş kaydedildi ve (uzak depo varsa) yüklendi mi? info: _kayit_bilgisi'nin sonucu."""
    if info is None:
        return False, ["❌ Git deposu yok ya da okunamadı: iş kaydedilmedi."]
    if not info["kayit_var"]:
        return False, ["❌ Henüz hiç kayıt (commit) yok."]
    lines = []
    staged, unstaged, untracked = [], [], []
    for line in info["degisen"]:
        name = line[3:].strip('"')
        if line.startswith("??"):
            untracked.append(name)
            continue
        if line[0] not in " ?":
            staged.append(name)
        if line[1] != " ":
            unstaged.append(name)
    if staged:
        lines.append(f"❌ Eklenmiş ama kaydedilmemiş değişiklik ({len(staged)} dosya): {_liste(staged)}.")
    if unstaged:
        lines.append(f"❌ Eklenmemiş ve kaydedilmemiş değişiklik ({len(unstaged)} dosya): {_liste(unstaged)}.")
    if untracked:
        lines.append(
            f"❌ Git'e hiç eklenmemiş yeni dosya ({len(untracked)}): {_liste(untracked)}. Göreve aitse ekleyip kaydedin; "
            "kaydedilmemesi gerekiyorsa .gitignore'a yazın."
        )
    if info["dal"] is None:
        lines.append("❌ Şu an bir dalda değilsiniz (HEAD ayrık): kayıtlar bir dala bağlı değil.")
    elif not info["uzak_var"]:
        lines.append("ℹ️ Uzak depo (GitHub) yok: kayıtlar yalnız bu bilgisayarda; yükleme denetlenmedi.")
    elif info["uzak"]["ileride"] is None:
        lines.append(f"❌ '{info['dal']}' dalı uzak depoda yok ({info['uzak']['ref']}): hiç yüklenmedi.")
    elif info["uzak"]["ileride"]:
        lines.append(
            f"❌ {info['uzak']['ileride']} kayıt yüklenmedi ({info['uzak']['ref']} gerisinde kalıyor). 'git push' ile yükleyin; "
            "güvenlik kutusunda yüklenemiyorsa kullanıcıya söyleyin."
        )
    ok = not any(line.startswith("❌") for line in lines)
    if ok:
        where = f" ve yüklendi ({info['uzak']['ref']}; son bilinen duruma göre, ağa çıkılmadı)" if info["uzak"] else ""
        lines.insert(0, f"✅ Her şey kaydedildi{where}.")
    return ok, lines


def _kayit_bilgisi(root: Path) -> dict | None:
    try:
        if _git_output(root, "rev-parse", "--is-inside-work-tree") != ["true"]:
            return None
        status = [line for line in _git_output(root, "status", "--porcelain", "--no-renames") if line.strip()]
        branch = (_git_output(root, "branch", "--show-current") or [""])[0].strip() or None
        remotes = _git_output(root, "remote")
    except (subprocess.CalledProcessError, OSError):
        return None
    head = _head(root)
    info = {"degisen": status, "kayit_var": head not in (None, "yok"), "dal": branch, "uzak_var": bool(remotes), "uzak": None}
    if not (remotes and branch and info["kayit_var"]):
        return info
    upstream = subprocess.run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=root,
                              capture_output=True, encoding="utf-8", errors="replace")
    ref = upstream.stdout.strip() if upstream.returncode == 0 and upstream.stdout.strip() else \
        f"{'origin' if 'origin' in remotes else remotes[0]}/{branch}"
    try:
        _git_output(root, "rev-parse", "-q", "--verify", f"refs/remotes/{ref}")
        ahead = int(_git_output(root, "rev-list", "--count", f"refs/remotes/{ref}..HEAD")[0])
    except (subprocess.CalledProcessError, OSError, IndexError, ValueError):
        ahead = None  # dal uzak depoda yok
    info["uzak"] = {"ref": ref, "ileride": ahead}
    return info


def _kayittan_beri_degisen(root: Path, tree: str) -> list[str] | None:
    """Testlerin denediği ağaçla diskteki takip edilen dosyalar arasındaki fark; ağaç yoksa (silinmiş) None."""
    try:
        return _git_output(root, "diff", "--name-only", "--no-renames", tree)
    except (subprocess.CalledProcessError, OSError):
        return None


GOREV_ARAMA_SINIRI = 200  # kayıt; ILERLEME.md'ye dokunan bu kadar kayıtta değişmediyse en eskisi başlangıç sayılır


def _gorev_baslangici(root: Path) -> str | None:
    """Görevin başladığı kayıt: ILERLEME.md › 'Şu anki görev' bölümünün en son değiştiği kayıt (ana dal çizgisinde).
    O kayıt sayılmaz: görev genelde önceki görevin kapanış kaydında yazılır (teslim.md adım 5)."""
    try:
        commits = _git_output(root, "log", "--first-parent", f"-{GOREV_ARAMA_SINIRI}", "--format=%H", "--", ".waypoint/ILERLEME.md")
    except (subprocess.CalledProcessError, OSError):
        return None
    newer = None  # (kayıt, bölüm)
    for commit in commits:
        try:
            text = _git_bytes(root, "show", f"{commit}:.waypoint/ILERLEME.md").decode("utf-8", errors="replace")
        except (subprocess.CalledProcessError, OSError):
            text = ""  # bu kayıtta dosya silinmiş
        section = "\n".join(line.rstrip() for line in _section(text, "Şu anki görev").splitlines()).strip()
        if newer is not None and section != newer[1]:
            return newer[0]
        newer = (commit, section)
    return newer[0] if newer else None


def _ust_klasor(name: str) -> str:
    return name.split("/", 1)[0] if "/" in name else "(kök)"


def _dosya_turu(name: str) -> str:
    if _not_mu(name):
        return "Not"
    if _is_test_file(name):
        return "Test"
    return "Kod" if _is_code_file(name) else "Diğer"


def gorev_raporu(gorev: str, baslangic: str | None, kaydedilen: list[str], kaydedilmemis: list[str],
                 testsiz: list[str]) -> list[str]:
    """3. bölüm (yalnız bilgi, kapıyı kapatmaz): görev başladığından beri değişen dosyalar ve göze çarpan durumlar."""
    lines = [f"Şu anki görev: {gorev or '(boş)'}"]
    if baslangic is None:
        return lines + ["ℹ️ Görevin başladığı kayıt bulunamadı (ILERLEME.md hiç kaydedilmemiş); dosyalar listelenmedi."]
    names = list(dict.fromkeys(name.replace("\\", "/") for name in [*kaydedilen, *kaydedilmemis]))
    lines.append(
        f"Görev başlangıcı: {baslangic} ('Şu anki görev' bölümünün son değiştiği kayıt; onun dosyaları sayılmaz). "
        f"O zamandan beri değişen {len(names)} dosya:"
    )
    groups = {kind: [name for name in names if _dosya_turu(name) == kind] for kind in ("Kod", "Test", "Not", "Diğer")}
    lines += [f"- {kind} ({len(items)}): {_liste(items, 10)}" for kind, items in groups.items() if items]
    if not names:
        lines.append("ℹ️ Görev başladığından beri hiçbir dosya değişmedi.")
    tested_code = [name for name in groups["Kod"] if not any(name.startswith(folder) for folder in testsiz)]
    if tested_code and not groups["Test"]:
        lines.append(
            f"⚠️ Kod değişti ama hiçbir test dosyası değişmedi ({_liste(tested_code, 5)}): yeni davranış testle denenmiyor "
            "olabilir. Gerekmiyorsa nedenini kullanıcıya bir satırla söyleyin."
        )
    folders = {_ust_klasor(name) for name in kaydedilen}
    # Notlar (README, ILERLEME.md) her görevde değişebilir; yalnız kod ve diğer dosyalar sayılır.
    outside = [name for name in kaydedilmemis if folders and not _not_mu(name) and _ust_klasor(name) not in folders]
    if outside:
        lines.append(
            f"⚠️ Bu görevin kayıtlarının dokunmadığı yerlerde kaydedilmemiş değişiklik var: {_liste(outside, 5)}. Göreve ait "
            "değilse ayrı kaydedin ya da kullanıcıya sorun."
        )
    return lines


def bitti_raporu(testler: tuple[bool, list[str]], kayit: tuple[bool, list[str]], gorev: list[str]) -> str:
    out = ["# Bitti kapısı (`kontrol.py --bitti`): iş gerçekten bitti mi?", "", "## 1. Testler bu içerikte çalıştı mı?",
           *testler[1], "", "## 2. İş kaydedildi mi?", *kayit[1], "", "## 3. Değişen dosyalar göreve ait mi? (yalnız bilgi)",
           *gorev, ""]
    failed = [name for ok, name in ((testler[0], "testler"), (kayit[0], "kayıt")) if not ok]
    if failed:
        out.append(
            f"❌ SONUÇ: Bitti DEĞİL ({' ve '.join(failed)}). Düzeltebildiğinizi düzeltip tekrar çalıştırın; kalanı kullanıcıya "
            "\"bitti\" demeden, bu rapordaki gibi sade dille söyleyin."
        )
    elif testler[1][0].startswith("⚠️"):
        out.append(
            "⚠️ SONUÇ: Kapı geçti ama TESTSİZ: iş kaydedildi, testler bu içerikte çalışmadı (1. bölüm). Kullanıcıya \"testler "
            "geçti\" demeyin; neden çalışmadığını ve öbür ⚠️ satırlarını söyleyin."
        )
    else:
        out.append("✅ SONUÇ: Kapı geçti. Kullanıcıya testlerin ve kaydın durumunu bu rapordaki gibi söyleyin; ⚠️ satırlarını da.")
    return "\n".join(out)


def bitti(root: Path) -> int:
    """'Bitti' demeden önce: testler bu içerikte geçti mi, iş kaydedildi mi, değişen dosyalar neler. 1 ve 2 kapıyı kapatır."""
    progress = _oku(root, ".waypoint/ILERLEME.md") or ""
    path = _isaret_yolu(root, SON_TEST)
    try:
        record = son_test_oku(path.read_text(encoding="utf-8")) if path is not None else None
    except OSError:
        record = None
    changed = _kayittan_beri_degisen(root, record["agac"]) if record else None
    testsiz = testsiz_klasorler(progress)
    testler = test_durumu(record, test_komutunu_bul(progress), changed, testsiz)
    info = _kayit_bilgisi(root)
    kayit = kayit_durumu(info)
    task = _dolu_satirlar(_section(progress, "Şu anki görev"))
    task_line = " ".join(" ".join(task).split()[:30])
    start = _gorev_baslangici(root) if info and info["kayit_var"] else None
    committed: list[str] = []
    label = None
    if start is not None:
        try:
            committed = _git_output(root, "diff", "--name-only", "--no-renames", start, "HEAD")
            label = (_git_output(root, "log", "-1", "--format=%h %ad %s", "--date=short", start) or [start[:7]])[0]
        except (subprocess.CalledProcessError, OSError):
            label = None
    uncommitted = [line[3:].strip('"') for line in (info["degisen"] if info else [])]
    report = bitti_raporu(testler, kayit, gorev_raporu(task_line, label, committed, uncommitted, testsiz))
    print(report)
    verdict = report.splitlines()[-1]
    oto_kayit(root, "BITTI", [verdict])
    return 1 if verdict.startswith("❌") else 0


_PYTHON_HOOK_KLASORU = "waypoint-hooks-py"
_HOOK_ADLARI = ("pre-commit", "commit-msg", "post-commit", "post-checkout", "post-merge", "post-rewrite",
                "pre-merge-commit", "pre-push", "pre-rebase", "prepare-commit-msg")
# Git for Windows ilk satırdaki yolun son parçasını PATH'te arar ('python'), yani bu dosyayı 'sh' olmadan başlatır.
# Mac ve Linux'ta bu yol olmayabilir; bu yüzden bu hook'lar yalnız 'sh' açılamayan Windows ortamlarında kullanılır.
# .git içinde dururlar: dal değişimi, stash, clean ya da yeni bir çalışma kopyası onları silip kontrolleri sessizce kapatamaz.
# Kontrolü çalışılan kopyadaki kontrol.py yapar; onu bilmeyen eski bir sürümde kayıt sessizce geçmesin diye durur.
_PYTHON_HOOK_METNI = """#!/usr/bin/python
# Waypoint: runs the same checks as .waypoint/hooks without sh, which some Windows sandboxes block. See kontrol.py --kutu-uyumu.
import os
import runpy
import sys

name = os.path.basename(__file__)
kontrol = os.path.abspath(os.path.join(".waypoint", "hooks", "kontrol.py"))  # git runs hooks from the working copy's top folder
if not os.path.isfile(kontrol):  # a branch without Waypoint: same as the normal hooks, which aren't there either
    sys.exit(0)
with open(kontrol, encoding="utf-8") as source:
    knows_hooks = '"--hook"' in source.read()
if not knows_hooks:
    print("Waypoint on this branch is too old for this sandbox's hooks; update it with kontrol.py --guncelle or merge the main branch.")
    sys.exit(1 if name in ("pre-commit", "commit-msg") else 0)
sys.argv[:1] = [kontrol, "--hook", name]
runpy.run_path(kontrol, run_name="__main__")
"""


def _hook_yolu(root: Path) -> str | None:
    try:
        return next(iter(_git_output(root, "config", "--get", "core.hooksPath")), None)
    except (subprocess.CalledProcessError, OSError):
        return None


def _python_hook_klasoru(root: Path) -> Path:
    """Bütün çalışma kopyalarının paylaştığı .git içinde."""
    common = _git_output(root, "rev-parse", "--git-common-dir")[0]
    return (root / common).resolve() / _PYTHON_HOOK_KLASORU


def _python_komutu_var(which=shutil.which) -> bool:
    """Hook'un ilk satırı PATH'te 'python' arar; 'py -3' ya da Microsoft Store kısayolu burada işe yaramaz."""
    found = which("python")
    if not found or Path(found).suffix.lower() != ".exe":  # git yalnız .exe arar; python.bat gibi kısayollar başlatılamaz
        return False
    try:
        result = subprocess.run([found, "--version"], capture_output=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and f"{result.stdout}{result.stderr}".startswith("Python 3")


def _hook_yolunu_yaz(root: Path, value: str) -> bool:
    command = ["git", "-C", str(root), "config", "core.hooksPath", value]
    return subprocess.run(command, capture_output=True, check=False).returncode == 0


def kutu_uyumu(root: Path, engelli=_sh_engelli, python_var=_python_komutu_var, windows: bool = os.name == "nt") -> str | None:
    """'sh' açılamıyorsa hook'ları 'sh' gerektirmeyen Python hook'larına geçirir; ne olduysa mesajını döndürür.
    Sıradan projelerde hiçbir şey değişmez. Projenin kendi hook yolu olan yerlere dokunulmaz.
    Proje klasörü taşındıysa eski yol bir şey çalıştırmaz: burada yeni yerine yazılır."""
    current = _hook_yolu(root)
    gecildi = Path(current or "").name == _PYTHON_HOOK_KLASORU
    if current != ".waypoint/hooks" and not gecildi:
        return None
    if not windows:  # bu hook'lar Mac ve Linux'ta çalışmaz: proje oraya kopyalandıysa normal hook'lara dönülür
        if not gecildi:
            return None
        if _hook_yolunu_yaz(root, ".waypoint/hooks"):
            return "🔧 Kayıt kontrolleri bu bilgisayarda normal hook'lara döndürüldü (.waypoint/hooks)."
        return ("⚠️ Kayıt kontrolleri şu an çalışmıyor: Git ayarı değiştirilemedi (.git/config kilitli ya da yazılamıyor). Kilidi "
                "kaldırıp 'git config core.hooksPath .waypoint/hooks' komutunu çalıştırın.")
    try:
        folder = _python_hook_klasoru(root)
    except (subprocess.CalledProcessError, OSError, IndexError):
        return None
    if gecildi and Path(current) == folder and all((folder / name).is_file() for name in _HOOK_ADLARI):
        return None
    if not gecildi and not engelli():
        return None
    if not python_var():
        if gecildi and not engelli():  # klasör taşınmış, 'sh' çalışıyor: kontroller normal hook'larla sürer
            _hook_yolunu_yaz(root, ".waypoint/hooks")
            return "🔧 Kayıt kontrolleri normal hook'lara döndürüldü (.waypoint/hooks)."
        return ("⚠️ Bu ortam Git'in 'sh' programını engelliyor ve PATH'te 'python' yok; kayıtlar izin istemeden yapılamaz. "
                "Python 3'ü 'python' adıyla kurun (Windows'ta \"Add python.exe to PATH\").")
    try:
        folder.mkdir(exist_ok=True)
        for name in _HOOK_ADLARI:
            with open(folder / name, "w", encoding="utf-8", newline="\n") as hook:
                hook.write(_PYTHON_HOOK_METNI)
    except OSError as exc:
        return f"⚠️ Bu ortam Git'in 'sh' programını engelliyor ve Python hook'ları yazılamadı ({exc}); kayıtlar izin istemeden yapılamaz."
    if not _hook_yolunu_yaz(root, folder.as_posix()):
        return ("⚠️ Python hook'ları yazıldı ama Git ayarı değiştirilemedi (.git/config kilitli ya da yazılamıyor). Kilidi kaldırıp "
                "'python .waypoint/hooks/kontrol.py --kutu-uyumu' komutunu yeniden çalıştırın.")
    return ("🔧 Bu ortam Git'in 'sh' programını engelliyor; kayıt kontrolleri 'sh' gerektirmeyen Python hook'larına geçirildi. "
            "Kontroller aynı; geri almak için: git config core.hooksPath .waypoint/hooks")


def _onceki_hook(root: Path, name: str, args: list[str]) -> int:
    """Waypoint'ten önceki proje hook'u varsa çalıştırır (.waypoint/hooks/onceki-hook, 'sh' ister)."""
    try:
        if not _git_output(root, "config", "--get", "waypoint.oncekiHooks"):
            return 0
    except (subprocess.CalledProcessError, OSError):
        return 0
    shell = kabuk_bul()
    if shell is None:
        print(f"❌ Projenin önceki '{name}' kontrolü çalıştırılamadı: 'sh' bulunamadı.")
        return 1
    returncode = subprocess.run([shell, ".waypoint/hooks/onceki-hook", name, *args], cwd=root, check=False).returncode
    if returncode in _KABUK_BASLAMADI:
        print(f"❌ Projenin önceki '{name}' kontrolü bu ortamda çalıştırılamadı ('sh' engelli). Bu kontrol kendi izninizle "
              "çalıştırılmalı; atlamayın.")
    return returncode


def mesaj_denetle(root: Path, path: Path) -> int:
    try:
        message = path.read_text(encoding="utf-8")
    except OSError:
        return 0
    try:
        staged_names = _git_output(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    except (subprocess.CalledProcessError, OSError):
        staged_names = []
    progress_text = _kayittaki(root, ".waypoint/ILERLEME.md") or ""
    errors, warnings = kayit_turu(message, staged_names, test_komutu(progress_text))
    text_errors, _ = bozuk_metin("Kayıt mesajı", message)
    errors.extend(text_errors)
    for error in errors:
        print(f"❌ {error}")
    for warning in warnings:
        print(f"⚠️ {warning}")
    oto_kayit(root, "UYARI", warnings)
    if errors:
        oto_kayit(root, "ENGEL", errors)
        return 1
    subject = next((line for line in message.splitlines() if line.strip() and not line.startswith("#")), "")
    oto_kayit(root, "KAYIT", [f"{subject} ({len(staged_names)} dosya)"])
    return 0


def _kayit_sonrasi(root: Path) -> None:
    """.waypoint/hooks/post-commit ile aynı iş: günlük sürüm denetimi, sonra GitHub'a yükleme."""
    if os.environ.get("WAYPOINT_NO_UPDATE_CHECK") != "1":
        message = surum_kontrolu(root, date.today().isoformat(), _github_surumu)
        if message:
            print(f"⬆️ {message}")
    if os.environ.get("WAYPOINT_NO_PUSH") == "1":
        return
    git = ["git", "-C", str(root)]
    if subprocess.run([*git, "remote", "get-url", "origin"], capture_output=True, check=False).returncode != 0:
        return
    branch = subprocess.run([*git, "symbolic-ref", "--short", "-q", "HEAD"], capture_output=True, encoding="utf-8",
                            errors="replace", check=False)
    if branch.returncode != 0:  # rebase ortası (dal yok): atla
        return
    name = branch.stdout.strip()
    push = subprocess.run([*git, "push", "-q", "origin", name], capture_output=True, encoding="utf-8", errors="replace",
                          check=False, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    if push.returncode == 0:
        oto_kayit(root, "YUKLE", [name])
        print(f"☁️ Kayıt GitHub'a yüklendi ({name}).")
        return
    lines = f"{push.stdout}{push.stderr}".strip().splitlines()
    oto_kayit(root, "YUKLENEMEDI", [f"{name}: {lines[-1] if lines else ''}"])
    print(f"⚠️ Kayıt alındı ama GitHub'a yüklenemedi ({name}). Güvenlik kutusundaysanız bu beklenir: kayıt bilgisayarda "
          "duruyor, kutu dışındaki bir sonraki kayıtta ya da 'git push' ile yüklenir. Değilse internet bağlantısını ve "
          "GitHub girişini kontrol edin.")
    print("\n".join(lines[-5:]))


def hook_calistir(root: Path, name: str, args: list[str]) -> int:
    """Python hook'larının girişi (bkz. kutu_uyumu); .waypoint/hooks'taki aynı adlı dosyaların yaptığını yapar."""
    returncode = _onceki_hook(root, name, args)
    if name == "pre-commit":
        return 1 if returncode != 0 else kayit_oncesi(root)
    if name == "commit-msg":
        return 1 if returncode != 0 else mesaj_denetle(root, Path(args[0]))
    if name == "post-commit":
        _kayit_sonrasi(root)  # eski hook'un sonucu yüklemeyi durdurmaz
        return 0
    return returncode


def main() -> int:
    # Windows konsolu emoji ve Türkçe karakterleri bozmasın
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    root = Path(__file__).resolve().parents[2]  # <proje>/.waypoint/hooks/kontrol.py
    if sys.argv[1:] == ["--surum"]:
        message = surum_kontrolu(root, date.today().isoformat(), _github_surumu)
        if message:
            print(f"⬆️ {message}")
        return 0
    if sys.argv[1:] == ["--guncelle"]:
        with tempfile.TemporaryDirectory() as folder:
            try:
                print(guncelle(root, waypoint_indir(Path(folder))))
            except GuncellemeHatasi as exc:
                print(f"❌ Güncelleme OLMADI: {exc}")
                return 1
        return 0
    if len(sys.argv) >= 3 and sys.argv[1] == "--hook":
        return hook_calistir(root, sys.argv[2], sys.argv[3:])
    if sys.argv[1:] == ["--kutu-uyumu"]:
        print(kutu_uyumu(root) or "Değişiklik gerekmedi.")
        return 0
    if sys.argv[1:] in (["--ozet"], ["--dogrula"]):
        message = kutu_uyumu(root)
        if message:
            print(message)
    if sys.argv[1:] == ["--ozet"]:
        print(oturum_ozeti(
            _oku(root, ".waypoint/ILERLEME.md") or "", _oku(root, ".waypoint/DERSLER.md") or "",
            _git_ozeti(root), _onbellekteki_surum(root),
        ))
        return 0
    if sys.argv[1:] == ["--temizlik"]:
        print(temizlik_raporu(_temizlik_bulgulari(root)))
        return 0
    if sys.argv[1:] == ["--test"]:
        return testleri_denetle(root)
    if sys.argv[1:] == ["--dogrula"]:
        return dogrula(root)
    if sys.argv[1:] == ["--bitti"]:
        return bitti(root)
    if sys.argv[1:] == ["--kayit-oncesi"]:
        return kayit_oncesi(root)
    if len(sys.argv) == 3 and sys.argv[1] == "--mesaj":
        return mesaj_denetle(root, Path(sys.argv[2]))
    return kurallari_denetle(root)


if __name__ == "__main__":
    sys.exit(main())
