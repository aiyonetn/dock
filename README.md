Baslangic: dock referans kareleri + gorev dosyasi

## AI limit paneli

Dock'un sonundaki kıvılcım ikonuna tıklayınca ChatGPT/Codex ve Claude için
`Session` (5 saatlik) ve `Weekly` (haftalık) kullanım çubukları açılır.

- **Codex:** `codex app-server` alt süreci JSON-RPC ile (`initialize` →
  `account/read` → `account/rateLimits/read`); plan ve `usedPercent` /
  `resetsAt` değerleri doğrudan gelir.
- **Claude:** `~/.claude/.credentials.json` içindeki `accessToken` ile
  `api.anthropic.com/api/oauth/usage` ucu okunur. Kimlik dosyası yoksa satır
  dürüstçe **"yapılandırılmadı"** yazar; uydurma yüzde üretilmez.
- **Elle yedek:** `~/.config/dock/limitler.json` içinde `claude.session` /
  `claude.weekly` sayıları varsa kimlik yokken bunlar kullanılır (kaynak: elle).
- Veriler ayrı thread'de okunur, 60 saniyede bir yenilenir; UI kilitlenmez.
- Token hiçbir yere yazdırılmaz (log/commit/ekran yok).
- Kart 320 px genişlikte, koyu `#0A0A0A` zemin ve 14 px köşe ile açılır;
  AI ikonunun üstünde ortalı konumlanır, ekran kenarına 12 px kalınca içeri kayar.
- Tipografi: 13 px başlık, 11 px etiket, 15 px bold yüzde, 10 px alt bilgi;
  çubuklar 8 px, %0'da bile 2 px başlangıç noktası gösterir. Açılış/kapanış
  120 ms `OutQuad` ile 6 px kayma animasyonu kullanır.
- Kart ve panel arka planı, dock görünür olmadan alınan ekran görüntüsünden
  8–12× küçült/büyüt blur ile üretilir; karta `%55`, panele `%80` `#0A0A0A`
  tonu bindirilir. Kart açıkken fon 500 ms'de bir yeniden kompozit edilir,
  kapalıyken yakalama yapılmaz.

## Müzik kartı

Dock'taki nota ikonuna tıklayınca "şimdi çalıyor" kartı açılır: albüm kapağı
(yoksa çizilmiş nota glifi), parça/sanatçı/albüm, 4 px ilerleme çubuğu, süreler
ve geri / oynat-duraklat / ileri düğmeleri.

- Gerçek oynatıcı varsa `org.mpris.MediaPlayer2.*` QtDBus arayüzünden
  Metadata/PlaybackStatus/Position okunur; düğmeler PlayPause/Next/Previous çağırır.
- Oynatıcı yoksa **demo modu** çalışır ("Midnight Drive · Demo", 3:48) ve kartın
  alt satırında `demo · oynatıcı yok` yazar; gerçek çalıyor izlenimi verilmez.
- AI limit ve müzik kartlarından yalnızca biri açık olabilir; dışına tıklamak kapatır.

### Müzik kartı cila

- Demo parça `Midnight Drive` / `Demo Player · Single`; "Demo · Demo" tekrarı yok.
- Kontrol grubu kart merkezine tam ortalı, eşit aralıklı; geri/ileri glifi 16 px,
  tıklama alanı 28×28, oynat 28 px daire.
- Alt satır/süreler `#9A9AA0`, footer `#8E8E93` ve 11 px.
- `kanit/dock-demo.mp4`: 15 sn, 1280×720 H.264; büyütme → müzik kartı → kapat →
  AI limit kartı → kapat sırasını gösterir (Xvfb `:99`, dikey offset 180).
