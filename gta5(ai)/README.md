# SOKAKLAR 2D

Python ve pygame ile yazılmış, yukarıdan bakışlı (top-down) 2D açık dünya aksiyon oyunu.
Tüm şehir, araçlar, karakterler, silah ikonları ve ses efektleri çalışma anında prosedürel
olarak üretilir; harici görsel veya ses dosyası gerekmez.

## Özellikler

- Prosedürel şehir: yollar, kaldırımlar, binalar, parklar, otoparklar ve sokak lambaları
- Yürüyerek keşif ve araç kullanma (ivme, sürtünme, el freni, kayma izleri, çarpışma hasarı)
- 3 kullanılabilir silah: tabanca, makineli tabanca, pompalı tüfek
  - Şarjör sistemi, otomatik şarjör değişimi, cephane toplama, geri tepme ve namlu efekti
  - İlk mermi her zaman nişangâhın tam üzerine gider; pompalıda diğer saçmalar yayılır
- Arabalara binme / inme, trafik araçları, park halindeki araçlar
- Yayalar ve polisler
  - Yayalar silah sesinden kaçar, araç altında kalabilir, can/para/cephane düşürebilir
  - Polisler A* yol bulma ile binaların etrafından dolaşır, ateş eder, yıldız arttıkça çoğalır
- 0-5 yıldızlı aranma sistemi, siren sesi ve ekran uyarıları
- Patlamalar, yangın, duman, kan, cesetler, kovanlar ve ekran sarsıntısı
- Can, zırh ve cephane kutuları; minimap; HUD; duraklatma, ölüm ve ana menü ekranları
- Tamamen sentezlenmiş ses efektleri (ses aygıtı yoksa oyun sessiz çalışmaya devam eder)

## Kurulum

Python 3.10 veya üstü önerilir.

```bash
python -m pip install -r requirements.txt
```

## Çalıştırma

Modüler sürüm:

```bash
python main.py
```

Tek dosyalık sürüm (önerilen):

```bash
python sokaklar_2d.py
```

Windows'ta `Oyunu_Baslat.bat` dosyasına çift tıklayarak da başlatabilirsiniz.

## Kontroller

| Tuş | İşlev |
| --- | --- |
| `WASD` / yön tuşları | Yürüme; araçta gaz / fren / direksiyon |
| Fare | Nişan alma |
| Sol tık | Ateş etme |
| `E` | Araca binme / inme |
| `Boşluk` | El freni (araçta) |
| `R` | Şarjör değiştirme |
| `1` `2` `3` | Silah seçme |
| Fare tekerleği | Silah değiştirme |
| `M` | Sesi açma / kapatma |
| `ESC` | Duraklatma (menüde çıkış) |
| `F3` | Hata ayıklama bilgisi |

Ölüm ekranında `R` ile yeniden başlayabilir, `Q` ile ana menüye dönebilirsiniz.

### God Mode

Oyun sırasında klavyeden `8828` yazın: karakter hasar almaz ve mermiler tükenmez.
Aynı kodu tekrar yazınca god mode kapanır. HUD'da `GOD MODE` ve `∞` göstergesi görünür.

## Oynanış İpuçları

- Polislerden kaçmak için araçları kullanın; aranma yıldızları zamanla azalır.
- Şarjör bitince silah otomatik olarak doldurulur, ancak yedek cephane gerekir.
- Hasarlı araçlardan duman çıkar. Patlamadan önce araçtan inin.
- Can, zırh ve cephane kutuları minimapte renkli noktalar olarak görünür.
- Yayalar silah sesinden korkar; kalabalıkta ateş etmek polisleri üzerinize çeker.

## Proje Yapısı

```
main.py                 Oyun başlatıcı (modüler sürüm)
sokaklar_2d.py          Tek dosyalık, bağımsız oyun sürümü
Oyunu_Baslat.bat        Windows için çift tıklanabilir başlatıcı
requirements.txt        Python bağımlılıkları
smoke_test.py           Başsız görüntü / oynanış testi
cop_test.py             Polis A* yaklaşma testi
gta2d/
  game.py               Oyun döngüsü, input, spawn, hasar, patlama, kamera
  settings.py           Ekran, şehir, silah ve araç ayarları
  city.py               Prosedürel şehir, render, minimap, çarpışma, A*
  entities.py           Oyuncu, araçlar, NPC'ler, mermiler, parçacıklar
  hud.py                HUD, minimap, menü / duraklatma / ölüm ekranları
  art.py                Prosedürel sprite ve ikon çizimleri
  audio.py              Prosedürel ses motoru
  utils.py              Yardımcı çizim, metin ve matematik fonksiyonları
```

## Testler

Başsız (headless) modda çalışır ve ekran görüntülerini
`%TEMP%\opencode\gta2d_shots` klasörüne kaydeder:

```bash
python smoke_test.py
python cop_test.py
```

`smoke_test.py` menü, yürüme, araç sürme, ateş etme, polis yaklaşması, yakın patlama
ve ölüm ekranlarını üretir. `cop_test.py` polislerin hedefe yaklaşma mesafesini saniye
saniye yazdırır.
