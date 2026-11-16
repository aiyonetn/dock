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
