# GÖREV v2: dock'u referansa benzet (3 madde + kanıt)

Repo: `~/dock` · Dal: `omp/dock-mvp` · Tarih: 2026-11-16 · Önceki tur: panel ve büyütme çalışıyor, görünüm zayıf

## Mevcut durum (sıfırdan başlama)

- Çalışan kod `~/omp-isler/dock-dock-mvp` içinde, commit **yok**, `kanit/01-bos.png` … `03-tiklama.png` var.
- Panel çiziliyor, 10 ikon var, Mac tarzı büyütme çalışıyor. Sorun **görünüm kalitesi**.

## Yapılacak 3 madde

### 1. Harf kutularını kaldır — sadece gerçek ikonlu uygulamalar

Ekran görüntüsünde ikonların yarısı "A", "B", "D" harfli kutular. Bu kabul edilemez.

- Varsayılan listeyi gerçek ikonu olanlarla sınırla: `google-chrome`, `firefox`, `code`,
  `org.gnome.Terminal`, `vlc`, `gimp`, `libreoffice-writer`, `org.gnome.Nautilus`, `thunderbird`,
  `spotify`. İkon dosyası **bulunamayan uygulamayı listeden çıkar**, yerine harf kutusu koyma.
- En az 7 gerçek ikon çıkmalı. `/usr/share/icons/hicolor/{64x64,128x128}/apps`, `.../pixmaps` yeterli.
- İkon kalitesi: 64 px kaynak kullan, QML'de `smooth: true`, `mipmap: true`.

### 2. Cam görünüm (referanstaki gibi)

Şu an panel düz koyu dikdörtgen. Referansta: arkası bulanık, kenarında ince açık çizgi, üstte hafif ışık.

- `QScreen.grabWindow(0, panelX, panelY, w, h)` → `QImage` → 12 kat küçült + geri büyüt (ucuz blur) →
  %80 opak koyu katman (`#0e0e12` alfa 205) bindir → QML'e arka plan olarak ver, 1 sn'de bir tazele.
- Panel: `radius: 20`, `border.color: "#ffffff22"`, `border.width: 1`, üst kenarda ince açık gradyan
  (1 px, `#ffffff30` → `transparent`). Gölge: panelin altına 8 px, `#00000066`, blur 18.
- Pencere **opak** ve tam panel boyutunda kalacak (compositor yok kuralı).

### 3. Oran ve detaylar

- İkon 56 px, panel yüksekliği **76 px**, yan boşluk 12 px, ikonlar arası 8 px, panel ekran altından
  10 px yukarıda, ortalı.
- Büyütme sırasında **komşu ikonlar yana kaymasın**, sadece ölçek değişsin; büyüyen ikon panelden
  yukarı taşsın (panel kırpmasın).
- Açık uygulama göstergesi: ikonun altında 4 px daire (`#ffffffaa`), şimdilik yalnız Chrome için
  (pencere listesi `wmctrl -l` ile kontrol edilebilir; zor gelirse bu maddeyi atla ve raporda söyle).
- Boşta CPU **%2 altı**: blur tazeleme 1 sn'de bir olsun, her karede olmasın.

## Bitti ölçütü (kanıt zorunlu)

`kanit/` altında: `01-bos.png`, `02-hover.png` (xdotool ile 3. ikonun üstünde), `03-tiklama.png`,
`04-gizli.png`, `05-acik.png` (autoHide açık, fare alt kenarda), `06-60s.png`, `olcum.txt`
(`ps -o %cpu,rss -p <pid>`).

Kabul: `01-bos.png`'ta **en az 7 gerçek renkli ikon**, harf kutusu yok, panelde blur + kenar ışığı
görünüyor, panel 76 px, ekran altında ortalı. Bunu kendi gözünle `vision` ile doğrula; doğrulamadan
commit atma.

Commit: Türkçe mesaj, imza yok. Süre bütçesi: 35 dakika. Süre dolarsa çalışan hâli commit'le,
eksikleri raporda yaz.
