# DEVAM: dock MVP — kod yazıldı, çalıştırılmadı

Repo: `~/dock` · Dal: `omp/dock-mvp` · Tarih: 2026-11-16 · İlk denemeden ~20 dk sonra oturum kesildi

## Durum (sıfırdan BAŞLAMA, yazılanı kullan)

Worktree `~/omp-isler/dock-dock-mvp` içinde şu dosyalar hazır ve sözdizimi temiz:

- `main.py` (8 satır — giriş noktası)
- `dock/ana.py`, `dock/ayarlar.py`, `dock/model.py`, `dock/uygulamalar.py`
- `qml/Dock.qml`
- `calistir.sh`, `assets/ikon-yok.svg`, `.venv` (PySide6 **kurulu**)
- `refs/dock-*.png` (görsel referans), `gorevler/dock-mvp.md` (ana görev — kurallar orada geçerli)

Önceki oturum **hiç çalıştırmadı, ekran görüntüsü almadı, commit atmadı**. İşin özü bu: çalıştır,
gör, düzelt, kanıtla, commit'le.

## İlk komut

```bash
cd ~/omp-isler/dock-dock-mvp
LD_LIBRARY_PATH=$PWD/libs/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH \
DISPLAY=:99 QT_QPA_PLATFORM=xcb .venv/bin/python main.py
```

Arka planda çalıştır, 3 sn bekle, `DISPLAY=:99 import -window root kanit/01-bos.png` al ve **görüntüyü
kontrol et**: panel görünüyor mu, ikonlar var mı? Görünmüyorsa hatayı oku (Qt platform eklentisi
yüklenmiyor mu, QML hatası mı) ve düzelt — çökme çıktısını kaybetmemek için stderr'i dosyaya yaz.

## Bu turda YAPILACAKLAR (sırayla, hepsi zorunlu)

1. Dock'u çalıştır, hataları düzelt. Panel ekranın altında, cam görünümlü, ikonlarla görünmeli.
2. `kanit/` altına 6 kanıt üret (ana görevdeki tablo birebir geçerli):
   `01-bos`, `02-hover` (xdotool mousemove ile 3. ikonun üstü), `03-tiklama`, `04-gizli`, `05-acik`,
   `06-60s` + `olcum.txt` (boşta `ps -o %cpu,rss -p <pid>`).
3. Boşta CPU %2 altında değilse sebebini bul (timer/repaint döngüsü) ve düşür.
4. `README.md` yaz (çalıştırma, ayar alanları, X11 blur yaklaşımı, bilinen sınırlar).
5. Commit: Türkçe, konuşur gibi, yapay zekâ imzası YOK, `Co-Authored-By` YOK.

## Bu turda YAPILMAYACAKLAR

- **İkon arama optimizasyonuyla uğraşma.** Önceki oturum burada takıldı (tek ikon 18 sn).
  Basit çözüm yeterli: ikon aramasını ilk açılışta bir kez yap, sonucu
  `~/.cache/dock/ikonlar.json` dosyasına yaz, sonraki açılışta oradan oku. Arama yavaş kalırsa
  `~/.local/share/icons` + `/usr/share/icons/hicolor` + `/usr/share/pixmaps` dışına bakma.
- Panel/widget/kart ekleme, C++'a taşıma, Wayland kodu — hepsi sonraki görev.
- Sudo/apt yok.

## Stop-loss

- 35 dakika. Süre dolar ve dock çalışıyorsa: çalışan hâli + elde edilen kanıtlarla commit at,
  eksikleri son mesajda "yapılmadı" diye yaz. Çalışmayan hâli commit'leme.
- Qt platform eklentisi iki denemede yüklenmiyorsa (`LD_LIBRARY_PATH`, `QT_QPA_PLATFORM=xcb`),
  DUR ve tam hata çıktısını raporla — çatı değiştirme.
