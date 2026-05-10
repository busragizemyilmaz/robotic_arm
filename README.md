# Rover Robotik Kol

Logitech Attack 3 joystick ile kontrol edilen 6 motorlu robotik kol projesi.
ROS 2 üzerinde çalışır. İki paketten oluşur: `rover_control` (joystick → komut)
ve `rover_driver` (komut → Roboclaw motor sürücüsü).

**Kontrol bilgisayar ile Jetson ayrıdır** — launch dosyaları da buna göre ikiye ayrılmıştır.

---

## Proje Yapısı

```
robotic_arm/
├── rover_control/
│   ├── launch/
│   │   └── teleop.py    ← Bilgisayarda çalıştırılır (joy + teleop)
│   ├── rover_control/
│   │   ├── rover_teleop_mod1.py       ← Mod 1: Çift-buton mantığı
│   │   └── rover_teleop_mod2.py       ← Mod 2: İki-slot seçim mantığı
│   ├── setup.py
│   └── package.xml
│
└── rover_driver/
    ├── launch/
    │   └── driver.py     ← Jetson'da çalıştırılır (sadece driver)
    ├── rover_driver/
    │   ├── driver_node.py             ← Roboclaw USB sürücüsü
    │   └── roboclaw_3.py              ← Roboclaw kütüphanesi
    ├── setup.py
    └── package.xml
```

---

## Sistem Mimarisi

```
[ Bilgisayar ]                          [ Jetson (robot) ]
──────────────────────────────          ──────────────────────────────
joy_node  (/robotarm_joy)               rover_driver_node
    │                                         │
    ▼                                         │ /dev/ttyUSB0
rover_teleop_node                       ──────┤
    │                                    Roboclaw 0x80 → M4, M1
    │  /motor_komutlari (ROS 2 ağ)       Roboclaw 0x81 → M2, M3
    └──────────────────────────────────► Roboclaw 0x82 → M5, M6
                                         Roboclaw 0x83 → Gripper
```

> `/robotarm_joy` : Aynı ağda başka bir paket de `joy` kullandığı için topic çakışmasını
> önlemek amacıyla bu proje `/joy` yerine `/robotarm_joy` topic'ini kullanır.

---

## Kurulum ve Derleme

Her iki makinede de (bilgisayar ve Jetson) aşağıdakiler yapılır:

```bash
# Workspace'e kopyala
cp -r robotic_arm ~/ros2_ws/src/

# Derle
cd ~/ros2_ws
colcon build --packages-select rover_control rover_driver

# Ortamı yükle (her yeni terminalde tekrarlanmalı)
source install/setup.bash
```

---

## Çalıştırma

### 1. Jetson — Driver'ı başlat

```bash
# USB izni (her bağlantıda bir kez)
sudo chmod 666 /dev/ttyUSB0

# Driver node'u başlat
ros2 launch rover_driver driver.py
```

---

### 2. Bilgisayar — Kontrol'ü başlat

Joystick'in hangi `/dev/input/jsX` cihazında göründüğünü öğren:

```bash
ls /dev/input/js*
```

Ardından ilgili cihazı belirterek başlat (örnek `js1` için):

```bash
ros2 launch rover_control teleop.py joy_device:=/dev/input/js1
```

> `joy_device` parametresi **her zaman açıkça yazılmalıdır.**
> Boş bırakılırsa `joy_node` sistemdeki ilk joystick'i alır ve
> başka bir paket de joy kullanıyorsa yanlış cihaza bağlanabilir.

Ek seçenekler:

```bash
# Mod 1 ile başlatma
ros2 launch rover_control teleop.py joy_device:=/dev/input/js1 teleop_mode:=1

# Kalibrasyonlu başlatma
ros2 launch rover_control teleop.py joy_device:=/dev/input/js1 calibrate:=true

# Hızı düşürerek başlatma (test için)
ros2 launch rover_control teleop.py joy_device:=/dev/input/js1 motor_speed:=15000.0

# Her şey bir arada
ros2 launch rover_control teleop.py joy_device:=/dev/input/js1 teleop_mode:=1 motor_speed:=20000.0 calibrate:=true
```

---

## Kalibrasyon

Joystick fiziksel olarak tam merkez pozisyonunda değilken başlatılırsa
eksen okumaları kayar ve motor istemediğin yönde döner. Kalibrasyon
bu kaymayı ölçüp dosyaya kaydeder — bir kez yapılır, tekrar gerekmez.

### Ne zaman yapılır?
- İlk kurulumda
- Joystick değiştirildiğinde
- Motorlar yanlış yönde dönmeye başlarsa

### Nasıl yapılır?

1. Joystick'i USB'ye tak
2. Hiçbir yöne **basmadan** bırak (serbest, merkez pozisyon)
3. Şu komutu çalıştır:

```bash
ros2 launch rover_control teleop.py joy_device:=/dev/input/js1 calibrate:=true
```

Terminalde şunu görünce kalibrasyon tamamdır:

```
[rover_teleop_node] Kalibrasyon kaydedildi -> /home/kullanici/.ros/joystick_cal.txt
[rover_teleop_node] Kalibrasyon tamamlandi. Normal operasyona gecildi.
```

4. `Ctrl+C` ile kapat. Dosya `~/.ros/joystick_cal.txt` olarak kaydedildi.

Bundan sonraki tüm başlatmalarda kalibrasyon dosyası **otomatik yüklenir**,
`calibrate:=true` yazmana gerek kalmaz.

---

## Kontrol Modları

### Mod 1 — Çift Buton

Her motor için iki ayrı buton vardır: biri ileri, biri geri.
Butona **basılı tutulduğu sürece** motor döner, bırakınca durur.
Aynı anda birden fazla motoru sürmek için birden fazla butona
aynı anda basılabilir.

```
Logitech Attack 3 üzerindeki konumlar:

  [ TRG ]  ← Boş (ileride kullanılacak)

  [ 2 ][ 3 ]  ← M2 İleri / Geri
  [ 4 ][ 5 ]  ← M3 İleri / Geri
  [ 6 ][ 7 ]  ← M4 İleri / Geri
  [ 8 ][ 9 ]  ← M5 İleri / Geri
  [10 ][11 ]  ← M6 İleri / Geri

  Joystick Sol/Sağ (axes[0])  ← M1
```

---

### Mod 2 — İki Slot Seçim

Önce bir motor **seçilir**, sonra joystick ile kontrol edilir.
Aynı anda **2 motor birden** kontrol edilebilir:
- **Slot-A** → joystick ileri/geri
- **Slot-B** → joystick sağa/sola

```
Logitech Attack 3 üzerindeki konumlar:

  [ TRG ]  ← Boş (ileride kullanılacak)
  [ 2 ]    ← Boş (ileride kullanılacak)

  [ 3 ]  ← M1 seç / bırak
  [ 4 ]  ← M2 seç / bırak
  [ 5 ]  ← M3 seç / bırak
  [ 6 ]  ← M4 seç / bırak
  [ 7 ]  ← M5 seç / bırak
  [ 8 ]  ← M6 seç / bırak

  Joystick İleri/Geri (axes[1])  ← Slot-A'daki motoru döndürür
  Joystick Sol/Sağ   (axes[0])  ← Slot-B'deki motoru döndürür
```

**Örnek kullanım:**
1. Buton 3'e bas → terminalde `M1 -> Slot-A` yazar, joystick ileri/geri M1'i döndürür
2. Buton 5'e bas → terminalde `M3 -> Slot-B` yazar, joystick sağa/sola M3'ü döndürür
3. Buton 3'e tekrar bas → M1 Slot-A'dan çıkar, slot boşalır
4. İki slot doluyken yeni bir butona basarsan → terminalde uyarı verir, hiçbir şey değişmez, önce bir motoru bırakman gerekir

---

## Motor — Roboclaw Bağlantı Haritası

Roboclaw kartları USB üzerinden **daisy-chain** bağlıdır, her kartın ayrı adresi var.

| Roboclaw Adresi | M1 Çıkışı | M2 Çıkışı |
|---|---|---|
| 0x80 (128) | 4. Motor | 1. Motor |
| 0x81 (129) | 2. Motor | 3. Motor |
| 0x82 (130) | 5. Motor | 6. Motor |
| 0x83 (131) | Gripper  | —        |

> Gripper (data[8]) şu an kod tarafında devre dışıdır.
> Kart bağlantısı hazır, ileride aktif edilecek.

---

## Tüm Launch Parametreleri

### rover_control.launch.py (Bilgisayar)

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| `joy_device` | *(boş)* | Joystick cihaz yolu — **her zaman yaz** (ör: `/dev/input/js1`) |
| `teleop_mode` | `2` | `1` = Mod 1, `2` = Mod 2 |
| `calibrate` | `false` | `true` ise ilk joy mesajını offset olarak kaydeder |
| `motor_speed` | `30000.0` | Maksimum hız değeri (0 – 32767) |
| `axis_deadzone` | `0.15` | Joystick merkez ölü bölgesi (0.0 – 1.0) |
| `calibration_file` | `~/.ros/joystick_cal.txt` | Kalibrasyon dosyası yolu |

### rover_driver.launch.py (Jetson)

Parametre almaz. Sadece `driver_node`'u başlatır.

---

## Çalışırken Parametre Değiştirme

Node'u kapatmadan hız değiştirmek için:

```bash
ros2 param set /rover_teleop_node motor_speed 20000.0
```

---

## Sık Karşılaşılan Sorunlar

**USB izin hatası:**
```bash
sudo chmod 666 /dev/ttyUSB0
```

Port farklıysa bul:
```bash
ls /dev/ttyUSB*
```

---

**Joystick hangi js numarasında?**
```bash
ls /dev/input/js*
# Çıktıya göre joy_device parametresini ayarla:
ros2 launch rover_control teleop.py joy_device:=/dev/input/js1
```

---

**Motor ters dönüyor:**
`rover_driver/driver_node.py` içinde ilgili `DutyM1M2` çağrısında
değerin işaretini `+`/`-` olarak değiştir.

---

**Motorlar hiç hareket etmiyor, hata da yok:**
```bash
# Teleop'tan komut geliyor mu kontrol et:
ros2 topic echo /motor_komutlari

# Joy topic'i geliyor mu kontrol et:
ros2 topic echo /robotarm_joy
```

---

**Yanlış joystick'i alıyor (başka paket de joy kullanıyor):**

`joy_device` parametresini mutlaka açıkça belirt:
```bash
ros2 launch rover_control teleop.py joy_device:=/dev/input/js1
```

Bu proje `/joy` yerine `/robotarm_joy` topic'ini kullandığı için
diğer paketle topic çakışması yaşanmaz; ancak `joy_node`'un
doğru fiziksel cihaza bağlandığından emin olmak için `joy_device`
her zaman belirtilmelidir.