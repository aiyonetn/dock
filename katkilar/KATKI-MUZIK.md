# Katkı — `muzik.py` (dock müzik paneli veri katmanı)

MPRIS (DBus) üzerinden çalan parça bilgisi + oynat/duraklat/ileri/geri kontrolü.
Dock UI'ı bu modülü çağırır; modül hiçbir koşulda istisna fırlatmaz.

Dosyalar (hepsi `dock/katkilar/` altında):

| Dosya | Ne |
|---|---|
| `muzik.py` | modülün kendisi (tek bağımlılık: stdlib) |
| `muzik-test.py` | 54 kontrol: demo, gerçek mod, ayrıştırıcı, import saflığı, 2 sn timeout |
| `sahte-mpris.py` | test fixture: sahte MPRIS oynatıcı (dbus-python + GLib), uçtan uca doğrulama |

## API

```python
import muzik

muzik.durum()
# {"caliyor": bool, "baslik": str, "sanatci": str, "album": str,
#  "kapak": str|None, "konum_sn": float, "sure_sn": float,
#  "kaynak": "mpris"|"demo"|"yok"}

muzik.kontrol("oynat"|"duraklat"|"ileri"|"geri")   # -> bool
```

- `kaynak="mpris"` gerçek oynatıcı, `"demo"` sahte parça, `"yok"` oynatıcı/DBus/CLI yok.
- Bilinmeyen eylem, `None`, oynatıcı yok → `kontrol` `False` döner.
- `kaynak="yok"` iken `durum()` boş alanlarla gelir (`baslik=""`, `kapak=None`, `0.0`).

## Hangi DBus yolu, neden

Sunucuda `playerctl` yok. Python `dbus`/`dbus-next` paketine bağımlı olmamak için
**CLI yolu** seçildi:

1. **birincil: `gdbus`** — `org.freedesktop.DBus.Properties.GetAll` ile
   `PlaybackStatus` + `Metadata` + `Position` **tek çağrıda** gelir. Çıktısı tipli
   GVariant metni (`<'Playing'>`, `<int64 214000000>`, `@as []`), ayrıştırması güvenilir.
2. **yedek: `dbus-send`** — gdbus yoksa/başarısızsa. Formatı dağınık
   (`array [`, `dict entry(`, `variant   string "x"`); aynı ayrıştırıcı bu biçimi de okur.
3. **hiçbiri yoksa** → `kaynak="yok"`, çökme yok.

Çağrılar:

| İş | Çağrı |
|---|---|
| oynatıcı bul | `org.freedesktop.DBus.ListNames` → `org.mpris.MediaPlayer2.*` süz |
| oku | `Properties.GetAll org.mpris.MediaPlayer2.Player` |
| kontrol | `org.mpris.MediaPlayer2.Player.{Play,Pause,Next,Previous}` |

`playerctld` (proxy, gerçek oynatıcı değil) aday listesinin sonuna atılır; en fazla 3
aday denenir, `PlaybackStatus == "Playing"` olan ilk aday seçilir.

## Davranış sözleşmeleri

- **Import yan etkisiz**: `import muzik` hiçbir subprocess/DBus/ağ işi yapmaz; CLI ilk
  `durum()`/`kontrol()` çağrısında seçilir (`muzik._BACKEND is None` doğrulanabilir).
- **2 sn sınır**: her DBus çağrısı `subprocess.run(timeout=2)` + `gdbus --timeout 2`.
  Zaman aşımından sonra ikinci CLI denenmez (dock saniyede bir yokluyor, 2 sn daha
  harcamak istemez) → `durum()` en kötü **2.0 sn**.
- Oturum veriyolu yoksa `/run/user/<uid>/bus` varsa otomatik kullanılır (cron/no-login).
- `konum_sn`, `sure_sn`'den büyükse 0'a çekilir (bazı oynatıcılar bayat `Position` verir).
- `sanatci`: `xesam:artist` dizi ise `", "` ile birleştirilir.

## Demo mod

```bash
DOCK_MUZIK=demo python3 -c "import muzik; print(muzik.durum())"
```

3 parçalık sahte liste; ilk parça **Golden Hour Drive / Nova Lane / Sunset Boulevard /
214 sn** (sözleşmede istenen değerler). `konum_sn` gerçek zamana göre ilerler,
`duraklat` dondurur, `oynat` kaldığı yerden sürer, `ileri`/`geri` parça değiştirip
konumu sıfırlar. Tüm `kontrol` çağrıları `True` (bilinmeyen eylem hariç).

## Test

```bash
cd ~/dock/katkilar
python3 muzik-test.py                 # 54 kontrol, demo + gerçek + timeout
python3 sahte-mpris.py --dogrula      # kendi dbus-run-session'ında uçtan uca MPRIS
```

`sahte-mpris.py` sistem python3'ünde `dbus` (dbus-python) + `gi` ister; yoksa atlanır,
`muzik.py`'yi etkilemez.

## Sınırlar / bilinen eksikler

- **Kapak**: sadece `file://` ve dosya gerçekten varsa yol döner. `http(s)` URL'ler
  `None` (indirme UI tarafının işi), dosya yoksa `None`.
- **Yerel dosya oynatıcı yok**: sunucuda ses/oynatıcı olmadığı için gerçek mod burada
  yalnızca "oynatıcı yok" dalını gösterir; MPRIS yolu sahte oynatıcıyla doğrulandı.
- **`Position`** her oynatıcıda güncel değil (bazıları yalnızca `Seeked` sonrası
  günceller); bu yüzden UI'da konum çubuğunu kendisi ilerletmek isteyebilir.
- **Çoklu oynatıcı**: aynı anda 3'ten fazla oynatıcı varsa yalnızca ilk 3 aday denenir
  (2 sn × aday süresini sınırlamak için). Tercih edilen oynatıcıyı sabitlemek
  gerekirse `muzik.py`'ye "tercih listesi" eklenebilir.
- **Seek yok**: `kontrol` yalnızca istenen 4 eylemi destekler; konum atlama (Set/Seek)
  API'de yok.
- `Position` mikrosaniye → saniye çevrimi `int64` varsayar; `double` veren bozuk
  oynatıcılarda konum 0 görünebilir.
