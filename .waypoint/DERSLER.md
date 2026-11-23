# Dersler

## Kurallar (her oturumda oku — en fazla 20 satır)
- Oturum düşse de iş sürmeli: durumu `.waypoint/` dosyalarına yaz, tek uzun turda bitirmeye çalışma.
- Görsel iddia için `kanit/` altında ekran görüntüsü olmadan commit yok.
- Compositor yok: gerçek saydamlık/blur bekleme; `grabWindow` + küçült/büyüt simülasyonu kullan.
- `libxcb-cursor` sistemde yok: `libs/...` + `LD_LIBRARY_PATH`; sudo/apt deneme.
- Test sürecini PID ile durdur; geniş `pkill -f` kullanma.
- Headless testte `DISPLAY=:99`, `QT_QPA_PLATFORM=xcb` kullan.
- AI limitlerinde veri yoksa uydurma yüzde yazma; "yapılandırılmadı" de.
- Müzik demo modunu gerçek oynatıcı gibi gösterme; "demo · oynatıcı yok" yaz.
- Cam panel/ikon değişikliğinde önce `test.sh` kanıtlarını yenile.
- Pencereyi panelden büyük yapma; X11'de artan alan siyah görünür.
- Müzik kartında cam/blur/kapak rengi yok: zemin opak #1C1C1C, alt yüzey #2A2A2C, vurgu #4CC2FF.

## Kayıtlar

### 2026-11-16 — Oturum "Request was aborted" ile düştü
- Sorun: omp oturumu iş ortasında "Request was aborted" ile kesildi; yazılan kod çalıştırılmadan kaldı.
- Sebep: tek uzun turda iş yükü/oturum süresi.
- Çözüm: `gorevler/dock-mvp-devam.md` ile kaldığı yerden devam; durum `.waypoint/` formlarına yazıldı.
- Kural: her adımdan sonra durumu dosyaya yaz; işi yeniden başlatılabilir tut.

### 2026-11-16 — Saydamlık siyah çıktı
- Sorun: `WA_TranslucentBackground` ve panelden büyük pencere Xvfb `:99` üzerinde siyah göründü.
- Sebep: sistemde compositor yok; X11 yarı saydam pencereyi arka planla birleştiremiyor.
- Çözüm: opak pencere, panel kadar boyut, `grabWindow` + küçült/büyüt blur ve koyu katman.
- Kural: compositor yokken gerçek saydamlık/blur peşinde koşma; simülasyonu koru.

### 2026-11-16 — Qt xcb eklentisi açılmadı
- Sorun: PySide6 xcb platform eklentisi `libxcb-cursor` bulamadı; uygulama açılmadı.
- Sebep: paket sistemde yok, sudo/apt izni yok.
- Çözüm: `libs/usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0` + `LD_LIBRARY_PATH`; betiklere işlendi.
- Kural: çalıştırma ve test betiklerinde bu yolu her zaman ayarla.

### 2026-11-17 — Kanıtsız görsel commit
- Sorun: ikon/kart değişiklikleri ekran görüntüsü olmadan "oldu" sayıldı.
- Sebep: headless ortamda görsel sonuç ancak `import` ile görülüyor.
- Çözüm: `test.sh` 01-06 + `olcum.txt`; `kanit/` ve `docs/ekran/` görselleri.
- Kural: görsel iddia = kanıt görüntüsü; yoksa commit yok.

### 2026-11-21 — mpv-mpris boş artUrl döndürdü
- Sorun: gerçek mpv testinde `artUrl` boş `data:image/jpeg;base64,` geldi.
- Sebep: mpv-mpris 1.1 davranışı; kapak verisi taşınmıyor.
- Çözüm: uzak indirme yolu `DOCK_SAHTE_ARTURL` ile doğrulandı; demo/fallback korunuyor.
- Kural: gerçek oynatıcıda boş artUrl'i hata sanma; yolu ayrıca test et.

### 2026-11-21 — Geniş pkill test süreçlerini vurabilir
- Sorun: `test_v13.sh` `pkill -f mpv.AppImage` ve `pkill -f "http.server ..."` kullanıyor.
- Sebep: desen eşleşmesi geniş; PID saklanmıyor, başka süreçler de ölebilir.
- Çözüm: `test.sh` gibi `setsid` + `/tmp/*.pid` ile PID sakla ve `kill "$PID"` kullan.
- Kural: test süreçlerini PID ile durdur; `pkill -f` kullanma.

### 2026-11-21 — Müzik kartı saydam görünüm beğenilmedi
- Sorun: Eren cam/blur görünümü "bu saydamlık olarak kötü" diye reddetti.
- Sebep: kapak renginden türeyen yarı saydam katmanlar ve blur zemini okunurluğu düşürdü.
- Çözüm: düz `#1C1C1C` opak hap kart, 1 px `#3A3A3A` iç kenar, yalnız dış gölge; 6 düzen yeniden ölçülendi.
- Kural: müzik kartı zemininde alfa < 255 katman kullanma; kapak rengi zemine sızmamalı.

### 2026-11-21 — QML kök nesnede bağlam değişkeni yok
- Sorun: `kok.ikonSayisi` QML'de `undefined` döndü; `merkezX` NaN olup müzik kartı sol kenara düştü.
- Sebep: `ikonSayisi` kök nesnenin özelliği değil, motor bağlam değişkeni; `kok.` ile erişilmez.
- Çözüm: `ikonSayisi` doğrudan kullanıldı; kart konumu sabit ikon yuvasına bağlandı.
- Kural: bağlam değişkenlerini (`ikonSayisi`, `kopru`, modeller) `kok.` öneki olmadan kullan.
