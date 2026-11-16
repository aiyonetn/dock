# EK GÖREV 2: ekran görüntüsüne göre 3 somut hata

Dock'u ben çalıştırdım, ekran görüntüsü aldım. Üç hata var, bu üçünü düzelt:

## 1. Pencere boyutu panelden büyük → dışarısı SİYAH

X11'de pencere var: `Position: 280,680  Geometry: 879x196`. İçerik ise 76 px'lik panel ve o da
pencerenin altında. Pencerenin geri kalanı **siyah** çıkıyor, çünkü `:99` ekranında **compositor yok** —
yarı saydam pencere şeffaf görünmez, siyah olur.

Çözüm: pencere boyutu = panel boyutu (içerik kadar). `QWidget.resize(panelGenislik, panelYukseklik)`
ve paneli pencerenin tamamına yay. Dışarıda boş alan kalmasın. Konum: ekranın altı, ortalı.

## 2. Saydamlık/blur yaklaşımı yanlış

`WA_TranslucentBackground` bu ekranda siyah veriyor. Şununla değiştir:

- Pencere **opak** olsun, arka planı panelin kendi çizdiği koyu yarı mat renk
  (`#101014` → `#1b1b22` dikey gradyan, %92 opak his).
- Arka plan bulanıklığı: `QScreen.grabWindow(0, panelX, panelY, w, h)` ile panelin arkasındaki bölgeyi
  al, `QImage`'ı 8-12 kat küçültüp geri büyüt (ucuz blur), üstüne %78 opak koyu katman bindir.
  Bu görüntüyü QML'e ver. **Böylece cam hissi opak pencerede de çıkar.**
- Köşe yarıçapı için QML'de `Rectangle { radius: 22 }` + `layer.enabled: true` + maske yeterli
  (pencere opak olduğu için köşeler siyah kalır — bu yüzden köşe yerine **4-6 px yuvarlatılmış
  dikdörtgen + kenar çizgisi** kullan, tam şeffaf köşe peşinde koşma).

## 3. İkonlar hiç görünmüyor (`ikonSayisi = 0`)

Ekran görüntüsünde tek bir parlayan kapsül var, ikon yok. Model boş kalıyor. Şunu yap:

- Açılışta **tarama beklemeden** 8 uygulamayı sabit bir varsayılan listeyle doldur
  (`google-chrome`, `firefox`, `org.gnome.Nautilus`, `code`, `org.gnome.Terminal`,
  `org.xfce.about`, `vlc`, `gimp` — var olanı al, olmayanı atla, en az 5 ikon çıksın).
- `tara()` işini ayrı bir `QThread`/zamanlayıcı ile sonra çalıştır, bitince modeli güncelle.
- İkon yolu bulunamazsa `assets/ikon-yok.svg` yerine **harf içeren renkli kutu** çiz
  (uygulama adının ilk harfi) — boş kapsül görünmesin.

## Bitti ölçütü (bu tur)

`DISPLAY=:99 import -window root kanit/01-bos.png` alındığında: ekranın altında ortalı, koyu cam panel,
**en az 5 ikon** görünüyor ve pencerenin dışında siyah alan yok. Bunu görmeden commit atma.

Süre: 15 dakika. Bitmezse neyin takıldığını tek cümleyle yaz.
