# EK GÖREV: tarama yavaşlığını kes ve dock'u çalıştır

`tara(56)` 50 saniyeden uzun sürüyor — bu yüzden dock'u bir türlü çalıştıramıyorsun. Ölçümü bırak,
şu basit yolu uygula ve **dock'u çalıştır**:

1. `.desktop` taramasını en fazla 40 dosyayla sınırla (`sorted(glob)[:40]`), `os.scandir` ile tek geçiş.
2. İkon arama sırası (ilk bulduğunu kullan, ağaçta dolaşma):
   - `Icon=` mutlaksa: `/usr/share/pixmaps/<ad>.{png,svg}`
   - `/usr/share/icons/hicolor/{48x48,64x64,128x128}/apps/<ad>.{png,svg}`
   - `/usr/share/icons/<tema>/<boyut>/apps/<ad>.{png,svg}` — sadece `hicolor` ve `Adwaita`
   - bulunamazsa `assets/ikon-yok.svg`
3. Sonucu `~/.cache/dock/ikonlar.json`'a yaz; dosya varsa hiç tarama yapma (açılış < 300 ms).
4. Hedef: `tara()` toplam süresi **2 saniyenin altında**. Bunu ölç ve raporla.

Sonra asıl işe dön: dock'u çalıştır, 6 kanıt görüntüsünü üret, README, commit. Optimizasyon
tartışması bitti — 2 saniye altına indiyse yeter.
