# İlerleme

## Proje hedefi
Linux X11 masaüstü için macOS tarzı cam dock: uygulama ikonları, büyütme, otomatik gizlenme ve iki cam kart (AI kullanım limitleri, "şimdi çalıyor"). Eren'in günlük masaüstünde kullanılır; "bitti" = `./calistir.sh` ile açılıp ikonlar ve kartlar çalışıyor, `kanit/` altında kanıt var.

## Aşama
Yapılıyor

## Nasıl açılır
1. Proje klasöründe terminal aç, `./calistir.sh` çalıştır. Betik `DISPLAY=:99`, `QT_QPA_PLATFORM=xcb` ve `libs/` için `LD_LIBRARY_PATH` ayarlar; Xvfb `:99` açık olmalı.
2. Yedek yol: `LD_LIBRARY_PATH=$PWD/libs/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH DISPLAY=:99 QT_QPA_PLATFORM=xcb .venv/bin/python main.py`
3. İlk kurulum (venv yoksa): `/usr/bin/python3 -m venv .venv && .venv/bin/pip install PySide6`

## Testleri çalıştırma
- `./test.sh` — `kanit/01-bos.png` … `06-60s.png` + `olcum.txt` üretir; dock'u PID ile durdurur.
- `./test_v13.sh` — gerçek mpv + MPRIS + http artUrl; parça geçişi max/p95 gecikmesini yazar.
- Not: `test_v13.sh` hâlâ geniş `pkill -f` kullanıyor; PID tabanlı durdurmaya çevrilecek.

## Kararlar
- 2026-11-16: PySide6 (Qt6) + QML — mevcut stack; hızlı Python prototipi, QML ile cam panel/animasyon — README.
- 2026-11-16: Xvfb `:99` + opak pencere; cam görünüm `grabWindow` + küçült/büyüt blur ile simüle — compositor yok — README "Dürüst sınırlar".
- 2026-11-16: `libxcb-cursor` sistemde yok; repo içi `libs/` + `LD_LIBRARY_PATH` — sudo/apt yok — calistir.sh.
- 2026-11-16: AI limit kartı uydurma yüzde üretmez; veri yoksa "yapılandırılmadı" yazar — dürüstlük — README.
- 2026-11-21: Aynı anda yalnız bir kart açık; dışına tıklamak kapatır — sadelik — qml/Dock.qml.
- 2026-11-21: Görsel değişiklikte `kanit/` görüntüsü olmadan commit yok — kural — kanit/.
- 2026-11-21: Müzik kartı 6 görünüm tek kartta; seçim `QSettings("dock","muzik")` ile kalıcı — yeni ikon yok — qml/MusicKarti.qml.
- 2026-11-21: Ses/mikrofon `pactl` ile `dock/ses.py`; gerçek mikrofon yoksa `.monitor` yedeği ve "mikrofon yok" — çökme yok — dock/ses.py.
- 2026-11-21: Müzik kartı konumu sabit (büyütmesiz) ikon yuvasına göre; fare gezinirken kart zıplamaz — qml/Dock.qml.
- 2026-11-21: Müzik kartı **opak** #1C1C1C hap (lumabar düzeni); cam/blur/kapak rengi/gradyan kaldırıldı, zemin kapaktan bağımsız — qml/MusicKarti.qml.
- 2026-11-22: Panel ölçüsü saf `dock/olcu.py:hesapla` ile ekrana sığdırılır (ikon gerekirse küçülür, hover de sınır içinde, pencere ≤ ekran); köşe maskesi `setAlphaChannel` ile gerçekten yuvarlanır — qml/Dock.qml, dock/ana.py.

## Plan
- [x] 1. MVP dock: panel, ikon tarama, büyütme, tıklama, auto-hide — bitti sayılır: `test.sh` 01-06 + ölçüm.
- [x] 2. Görsel cila v2/v3: şeffaf ikon, gölge, cam panel, ölçüler — bitti sayılır: `kanit/01-bos.png` temiz, en az 7 ikon.
- [x] 3. AI limit kartı: Codex/Claude, halkalar, 60 sn yenileme — bitti sayılır: `kanit/ai.png`, `docs/ekran/ai-limit-karti.png`.
- [x] 4. Müzik kartı: MPRIS + demo, kapak, seek/kontroller — bitti sayılır: `kanit/muzik.png`, `docs/ekran/muzik-karti.png`.
- [x] 5. v13 kapak işleme + gecikme ölçümü — bitti sayılır: max 66.9 ms / p95 61.9 ms (<100 ms).
- [ ] 6. AI limit ve müzik panelindeki eksikler — bitti sayılır: açık maddeler tek tek kapanır, yeni kanıt gelir.
- [ ] 7. İkon optik eşitliği — bitti sayılır: tüm ikonlar aynı görsel ağırlıkta, kanıt görüntüsü var.
- [x] 8. Müzik kartı 6 görünüm (4 düzen + ses + mikrofon), opak hap v2 — bitti sayılır: `kanit/muzik-{tam,kompakt,mini,bar}.png`, `kanit/ses-cikis.png`, `kanit/mikrofon.png`, `kanit/muzik-olcu.txt` (20 nokta alfa 255 + iki kapak); `test_muzik.sh` EXIT=0.

## Şu anki görev
Müzik kartı 6 görünüm tamamlandı (4 düzen + ses + mikrofon); kanıtlar `kanit/` altında.
Son commit `e218d83` (21 Kas 18:29); `master` = `origin/main` = `e218d83`.

## Sıradaki adım
AI limit kartındaki yazı çakışması ve kartların sağdan taşması (ayrı iş); ardından ikon optik eşitliği. (Öncelik Eren'de.)

## Sonra yapılacaklar (park edilen fikirler)
- Wayland + compositor altında gerçek backdrop blur; şimdiki cam görünüm simülasyon.
- Boş olmayan gerçek MPRIS `artUrl` ile `test_v13.sh` tekrarı (mpv-mpris boş data URL döndürüyor).
- İkon optik eşitliği: düşük kaplamalı/yuvarlak logoların görsel ağırlığı.
- `test_v13.sh` içindeki geniş `pkill -f` yerine PID tabanlı durdurma.

## Günlük
- 2026-11-16: PySide6/QML iskelet, `.desktop` tarama, büyütme, cam panel, ikon cilası, README ve ilk kanıtlar.
- 2026-11-21: AI limit ve müzik kartları, kavis/ölçü düzeltmeleri, ekran görüntüleri yenilendi; müzik kartı 6 görünüm + pactl ses/mikrofon + QSettings. Ardından müzik kartı opak #1C1C1C hap düzenine (lumabar) çevrildi; cam/blur kaldırıldı. Cila: ses çubuğu/mute, tam seçici-başlık ve bar süre-düğme boşlukları ölçülü ayrıldı.
- 2026-11-22: Opak müzik kartının 6 görünüm görüntüsü docs/ekran altına eklendi, README'ye Görünümler tablosu kondu; ses çıkışı + mikrofon + sistem kartı değişiklikleri tek commit'te toplandı. Panel ekran taşması düzeltildi: 1440'ta ikon 84→74, panel 1310, hover 1377, pencere 1439/x=0; köşe maskesi onarıldı (`kanit/dock-kose-{once,sonra}.png`, `dock-kose-olcu.txt`).
- 2026-11-23: Waypoint 1.73 katmanı, müzik testi kanıtları ve katkı dosyaları ilk kez kayda alındı; test günlükleri ve geçici test sandbox'ı (.gitignore) dışında tutuldu.
