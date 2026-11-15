# Görev: Masaüstü dock — MVP (PySide6 + QML)

Repo: `~/dock` · Dal: `omp/dock-mvp` (ompx açar) · Tarih: 2026-11-16
Referans: `refs/dock-02.png`, `refs/dock-05.png`, `refs/dock-12.png` (Windows için "lumabar" tanıtımından kırpılmış kareler — ÖNCE BUNLARA BAK)

## Sorun

Eren'in Linux masaüstünde macOS/Windows "smart dock" hissi veren bir alt çubuk istiyor: cam panel,
ikonlar, Mac tarzı büyütme, tıklayınca uygulama açma, istenirse otomatik gizlenme. Referans videodaki
görünüme mümkün olduğunca benzemeli. Bu görev yalnız **dock**; panel/widget **bu görevde yok**.

## Bağlam

- Sunucu headless: X ekranı `:99`, 1440x900 (`Xvfb :99 -screen 0 1440x900x24`). `DISPLAY=:99` ile çalıştır.
- Python 3.11 var, `pip --user` çalışıyor. **PySide6 (Qt6) kurulacak** (venv: `.venv`, `pip install PySide6`).
- Qt6'nın `libxcb-cursor` bağımlılığı sistemde YOK ve sudo yok. Bu yüzden repoda hazır:
  `libs/usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0` — çalıştırma betiği
  `LD_LIBRARY_PATH=$PWD/libs/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH` yapmalı. Sudo/apt DENEME.
- Ekran görüntüsü: `DISPLAY=:99 import -window root kanit/<ad>.png` (ImageMagick `import` var).
- Referans kareler 1280x720; dock yüksekliği ~80-90 px, ikon ~56 px, köşe yarıçapı ~22 px,
  cam panel (arkası hafif bulanık/koyu yarı saydam), ikonlar arası ~10 px, panel ekranın altında ortada
  ve kenarlardan ~24 px yukarıda.
- Bu proje **yeni ve boş** bir repo; başka projeye dokunma.

## İstenen (bitti ölçütü)

Tek dosya değil, çalışan bir uygulama: `./calistir.sh` ile açılır.

1. **Pencere:** çerçevesiz, her zaman üstte, görev çubuğu gibi davranır (`Qt.FramelessWindowHint |
   Qt.WindowStaysOnTopHint | Qt.Tool`), saydam arka plan (`WA_TranslucentBackground`). Pencere
   ekranın altında ortalanır, tam genişlik değil — içerik kadar.
2. **Görünüm (referansa benzer):** koyu, yarı saydam cam panel; yuvarlatılmış köşeler; ince açık kenar
   çizgisi; ikonlar arasında eşit boşluk. Panel arkasındaki masaüstünü bulanıklaştırmak için: panelin
   arkasındaki ekran bölgesini `QScreen.grabWindow(0, x, y, w, h)` ile al, `QML Image` üstünde
   `ShaderEffect`/`MultiEffect` bulanıklık uygula, 1 sn'de bir tazele. (X11'de gerçek backdrop blur
   yok; bu yaklaşım kabul.)
3. **İkonlar:** `/usr/share/applications/*.desktop` dosyalarını tara (`Icon=`, `Name=`, `Exec=` oku).
   İkon dosyasını tema yollarında ara (`~/.local/share/icons`, `/usr/share/icons`, `/usr/share/pixmaps`,
   png/svg). Bulunamayan ikon için `assets/ikon-yok.svg` gibi bir yer tutucu kullan. Varsayılan olarak
   ilk 10 uygulamayı göster; liste `~/.config/dock/ayar.json` içindeki `sabitlenen` alanından
   okunur (yoksa ilk 10).
4. **Mac tarzı büyütme:** fare bir ikonun üzerine gelince o ikon x1.9, komşuları azalan oranda büyür
   (gauss eğrisi), 120-160 ms yumuşak animasyon, imleç çıkınca eski hâline döner. Büyüme sırasında
   ikonlar panelin dışına taşabilir (panel kırpmamalı).
5. **Tıklama:** `.desktop`'un `Exec=` satırını temizle (`%U`, `%f` gibi alan kodlarını sil),
   `subprocess.Popen` ile başlat. Başlatılamazsa ikon 400 ms parlar (vurgu rengi) ve tooltip'te
   "başlatılamadı" yazar. Uygulama açıkken ikon altında küçük nokta göstergesi (opsiyonel, kolay yolu seç).
6. **Ayardosyası:** `~/.config/dock/ayar.json` — `{"autoHide": false, "iconSize": 56,
   "buyutme": 1.9, "kenarBosluk": 24, "sabitlenen": ["firefox.desktop", ...]}`. Dosya yoksa bu
   varsayılanlarla oluştur. Değişiklik uygulama yeniden başlatılınca geçerli (canlı izleme şart değil).
7. **Otomatik gizlenme:** `autoHide=true` ise panel ekranın altına gizlenir; fare ekranın en alt 2 px'ine
   gelince 200 ms'de yukarı kayar, fare panelden çıkınca 800 ms sonra tekrar gizlenir. `autoHide=false`
   iken hep görünür.
8. **Kararlılık:** 60 saniye açık kalır, çökmez, sürekli CPU tüketmez (boşta < %2, ölç ve raporla).

## Dokunma

- Başka repo/klasör yok (`~/mpv-android`, `~/bot`, `~/notes` vb. kesinlikle).
- `sudo`, `apt`, sistem geneli kurulum yok. Sadece `pip --user`/venv ve repo içi dosyalar.
- Wayland/layer-shell kodu yazma (compositor yok, test edilemez).
- Panel/widget/kart (hava durumu, medya, AI limits) **bu görevde yok** — sonraki görev.

## Doğrulama (kanıt zorunlu)

`./test.sh` şunları yapsın ve `kanit/` altına yazsın:

| Kanıt | Nasıl |
|---|---|
| `kanit/01-bos.png` | dock açık, fare hiçbir ikonda değil |
| `kanit/02-hover.png` | fare 3. ikonun üstünde (büyütme görünür) — `xdotool mousemove` ile |
| `kanit/03-tiklama.png` | bir ikona tıklandıktan sonraki hâl (başlatma ya da parlama) |
| `kanit/04-gizli.png` | `autoHide=true` ile gizli hâl |
| `kanit/05-acik.png` | `autoHide=true`, fare alt kenarda, panel görünür |
| `kanit/06-60s.png` | uygulama 60 sn sonra hâlâ ayakta |
| `kanit/olcum.txt` | boşta CPU/RAM (`ps -o %cpu,rss -p <pid>`) |

Ekran görüntüsü: `DISPLAY=:99 import -window root kanit/x.png`. Her kanıttan sonra
`vision` ile kendin bakmana gerek yok ama panelin gerçekten göründüğünü görüntü boyutundan/elle kontrol et.

Ek olarak `README.md` yaz: nasıl çalıştırılır, ayar alanları, bilinen sınırlar (X11 blur yaklaşımı).

## Rapor

Bitince kısa rapor: ne yapıldı · hangi kanıtlar üretildi (dosya yolları) · ölçülen boşta CPU/RAM ·
bilinen eksikler · Eren'in karar vermesi gereken noktalar. Raporu commit mesajına değil, son mesaja yaz.

## Stop-loss

- PySide6 kurulumu 10 dakikayı geçerse veya Qt platform eklentisi yüklenemezse: 2 deneme yap
  (önce `LD_LIBRARY_PATH` ile `libxcb-cursor`, sonra `QT_QPA_PLATFORM=xcb` açıkça) — hâlâ olmuyorsa
  DUR ve raporla, alternatif çatıya geçme.
- Toplam süre bütçesi 60 dakika. Süre dolarken dock çalışıyor ama 1-2 madde eksikse: çalışan hâli
  commit'le, eksikleri raporda "yapılmadı" diye yaz. Çalışmayan hâli commit'leme.
