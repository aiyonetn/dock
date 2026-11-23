# Harita

<!-- A table of contents for the code, so a new session finds where things are without opening every file.
     Keep it short: at most ~30 files and ~20 entry points; the commit check warns above that.
     Paths are relative to the project root; a folder ends with "/". The commit check refuses a listed file,
     folder or entry point that no longer exists, so fix the line when you move, rename or delete one.
     Update it only when an important file or entry point is added, removed or renamed, not for every change.
     Don't read it whole: search it for the name you need. Who calls what: search the code instead.

## Dosyalar
- src/app.js — uygulamayı başlatır, ekranları bağlar
- src/db/ — veritabanı okuma ve yazma

## Giriş noktaları
- girisYap() — src/auth.js — kullanıcı adı ve şifreyi kontrol eder — test: tests/giris.test.js
-->

## Dosyalar
- main.py — giriş noktası; `dock.ana.calistir()` çağırır
- README.md — tanıtım, ekran görüntüleri, çalıştırma, bilinen sınırlar
- calistir.sh — başlatıcı; Xvfb `:99`, `QT_QPA_PLATFORM=xcb`, `libs/` için `LD_LIBRARY_PATH`
- test.sh — 6 kanıt görüntüsü + boşta CPU/RAM ölçümü; dock sürecini PID ile durdurur
- test_v13.sh — gerçek mpv/MPRIS + http artUrl + parça geçişi gecikme testi
- test_muzik.sh — 6 müzik görünümü + pactl ses/mikrofon + gerçek mpv MPRIS kanıtı
- dock/ana.py — Dock penceresi, arka plan yakalama, cam kompozit, kart konumları, otomatik gizlenme
- dock/uygulamalar.py — `.desktop` tarama, ikon çözme, önbellek, uygulama başlatma
- dock/model.py — QML ikon listesi modeli (ad/ikon/çalıştı/parlama/hata/kimlik)
- dock/ikon.py — ikonları 256 px şeffaf, kırpılmış, optik dengeli PNG'ye işler
- dock/muzik.py — MPRIS okuma/kontrol, demo modu, kapak indirme/önbellek/renk, QSettings görünüm seçimi
- dock/ses.py — pactl çıkış/mikrofon okuma, hacim/mute ayarı, monitor yedeği
- dock/limitler.py — Codex JSON-RPC ve Claude OAuth limit okuma + elle yedek
- dock/limit_model.py — QML limit modeli ve 60 sn'lik arka plan yenileyicisi
- dock/ayarlar.py — `~/.config/dock/ayar.json` oku/kaydet/sınırla
- dock/x11.py — X11 Shape: giriş maskesi ve bounding bosaltma
- dock/tema.py — ortak yarıçap sabitleri (panel, kart, kapak)
- qml/Dock.qml — panel, ikon büyütme, kartları yerleştirme, tıklama ve ipucu
- qml/LimitKarti.qml — AI limit kartı: halkalar, plan, yenileme durumu
- qml/MusicKarti.qml — müzik kartı: opak #1C1C1C hap; 6 görünüm seçici (tam/kompakt/mini/bar + ses + mikrofon)
- qml/GolgeText.qml — 1 px koyu dış çizgili metin
- assets/ — `ikon-yok.svg`, `ai-limit.svg`, `muzik.svg`; `assets/fonts/` Geist + Geist Mono
- docs/ekran/ — README ekran görüntüleri (panel, müzik kartı, AI limit kartı)
- kanit/ — test kanıtları (PNG, `dock-demo.mp4`, `olcum.txt`); `kanit/arsiv/` eski kareler
- gorevler/ — arşivlenmiş görev dosyaları (MVP, devam, ekler, v2, v3, perf önerisi)
- libs/usr/lib/x86_64-linux-gnu/ — sistemde olmayan `libxcb-cursor.so.0` kopyası
- refs/ — tasarım referans kareleri (`dock-02/05/12.png`)
- olcum/kaydir.py — dock akıcılık/CPU ölçüm betiği

Not: katkilar/ klasörü müzik katkı notunu ve test yardımcılarını (sahte MPRIS, müzik testi) tutar; git izlemesinde değildir.

## Giriş noktaları
- `calistir()` — dock/ana.py — QApplication, fontlar, Dock ve event loop — çalıştırma: `./calistir.sh`
- `Dock` — dock/ana.py — pencere, arka plan, kartlar, auto-hide, X11 giriş maskesi
- `Kopru.tikla(indeks)` — dock/ana.py — QML tıklaması → uygulama başlat / hata parlaması
- `Kopru.panel_genislik` — dock/ana.py — QML → Python panel genişliği
- `Kopru.kart_konumu` — dock/ana.py — QML → Python kart geometrisi
- `Kopru.muzik_konumu` — dock/ana.py — QML → Python müzik kartı geometrisi
- `ArkaplanSaglayici.requestImage` — dock/ana.py — `image://arkaplan/{tam,panel,golge,kartGolge,muzikGolge}`
- `IkonModel` — dock/model.py — QML ikon modeli; tıklama ve durum tazeleme
- `tara()` / `secilenler()` / `baslat()` — dock/uygulamalar.py — tarama, seçim, süreç başlatma
- `hazirla()` — dock/ikon.py — ikon işleme ve önbellek yolu
- `MuzikModel` — dock/muzik.py — MPRIS/demo, kapak, `ara`/`oynat_duraklat`/`ileri`/`geri`, `gorunumSec`
- `SesModel` — dock/ses.py — pactl çıkış/mikrofon, `cikisAyarla`/`cikisMuteDegistir`/`kaynakMuteDegistir`
- `LimitModel` — dock/limit_model.py — QML limit verisi
- `LimitYonetici` — dock/limit_model.py — 60 sn yenileme
- `oku()` — dock/limitler.py — Codex ve Claude verisini birleştirir
- `yukle()` / `kaydet()` — dock/ayarlar.py — ayar dosyası
- `giris_maskesi()` — dock/x11.py — tıklama maskesi
