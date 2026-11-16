# GÖREV v3: ikonları "baskı" gibi durmaktan çıkar — şeffaf, gölgeli, oranlı

Repo: `~/dock` · Dal: `omp/dock-mvp` · Tarih: 2026-11-16 · Durum: v2 çalışıyor ve commit'li (`5c661cd`)

## Sorun (Eren'in geri bildirimi)

Paneldeki ikonlar cama **yapıştırılmış baskı** gibi duruyor:

1. Bazı ikonların arkasında **opak kare plaka** var (logo dışındaki alan şeffaf değil) — bu en çok göze batan şey.
2. İkonların altında gölge yok, panelden kopuk yüzüyorlar.
3. Boyutlar tutarsız: bazıları küçük kaynaktan büyütülmüş (bulanık/tırtıklı), bazıları kutuya tam oturmuyor.
4. Jenerik/sembolik ikonlar (baykuş, belge, arşiv) markasız duruyor.

## Yapılacaklar

### 1. Şeffaflık (asıl madde)

- İkon kaynağı seçiminde **sırayla**: `.svg` → 256/128 px PNG → 64 px PNG. 48 px altını hiç kullanma.
- SVG varsa `QSvgRenderer` ile 256 px'e render et, arka plan **şeffaf** olsun (`QImage(256,256,Format_ARGB32_Premultiplied)` + `fill(Qt.transparent)`).
- PNG'lerde opak kare plaka varsa temizle: köşe piksellerinin rengi tekdüzeyse (4 köşe arasındaki fark < 12),
  o rengi toleransla (%6-8 fuzz) şeffafa çevir. `QImage` ile alpha maskeleme yap; karmaşık araç kurma.
  Kenarlarda beyaz hâle kalırsa 1 px alpha erozyonu uygula (alpha <= 24 olan pikselleri sıfırla).
- Temizlik sonrası ikonun **çevresindeki boşluğu kırp** (alpha sınırlarından), sonra 56 px kutuya
  8 px iç boşlukla sığdır (oran korunur, ortalı). Böylece her ikon aynı görsel ağırlıkta olur.
- Sonuç yine de plakalı görünüyorsa o uygulamayı **listeden çıkar**, plakayla gösterme.

### 2. Gölge ve yuva

- Her ikonun altında `MultiEffect` (shadow) ya da QML `Rectangle` + blur: 1 px aşağı, 6 px blur,
  `#00000059`; ikon camın üstünde duruyormuş gibi olsun.
- İkonun arkasına 44x44 px, `radius: 12`, `#ffffff10` yuva; hover'da `#ffffff1f`. Plaka değil, çok hafif.

### 3. Uygulama listesi

- Gerçek ikonu olan, tanınan uygulamalar: `google-chrome`, `firefox`, `code`, `org.gnome.Terminal`,
  `vlc`, `spotify`, `gimp`, `libreoffice-writer`, `thunderbird`, `discord`, `telegram`, `steam`
  (kurulu olanları al). **En az 8** ikon çıksın, jenerik sembolik olanları alma.

## Bitti ölçütü

`kanit/` yenilenecek: `01-bos.png`, `02-hover.png`, `03-tiklama.png`, `olcum.txt`.
Kabul: `01-bos.png`'ta **hiçbir ikonun arkasında opak kare plaka yok** (hepsi şeffaf zeminli),
ikonlar eşit büyüklükte, altlarında yumuşak gölge var, en az 8 ikon. Bunu `vision` ile kendin doğrula
("ikonların arkasında kare plaka var mı?" diye sor) — doğrulamadan commit atma.

Bozuk/kirli hâli commit'leme. Commit mesajı Türkçe, imza yok. Bütçe: 30 dakika.
