# Rover Robotik Kol

Logitech Attack 3 joystick ile kontrol edilen 6 eksenli + gripper robotik kol projesi.
ROS 2 üzerinde çalışır. İki paketten oluşur:

- `rover_control` — joystick okuma ve motor komutları üretme (operatör bilgisayarında çalışır)
- `rover_driver` — motor komutlarını Roboclaw kartlarına iletme (Jetson'da çalışır)

---

## Proje Yapısı

```
robotic_arm/
├── rover_control/
│   ├── launch/
│   │   └── rover_control.launch.py    ← Bilgisayarda çalıştırılır
│   ├── rover_control/
│   │   ├── rover_teleop_mod1.py       ← Mod 1: Çift-buton mantığı
│   │   └── rover_teleop_mod2.py       ← Mod 2: İki-slot seçim mantığı (varsayılan)
│   ├── setup.py
│   └── package.xml
│
└── rover_driver/
    ├── launch/
    │   └── rover_driver.launch.py     ← Jetson'da çalıştırılır
    ├── rover_driver/
    │   ├── driver_node.py             ← Roboclaw USB sürücüsü
    │   └── roboclaw_3.py              ← Roboclaw kütüphanesi
    ├── setup.py
    └── package.xml
```

---

## Sistem Mimarisi

```
[ Operatör Bilgisayarı ]                        [ Jetson (robot üzerinde) ]
────────────────────────────────────            ─────────────────────────────────────
joy_node  (/mobility_joy)                       rover_driver_node
    │                                                 │
    ▼                                                 │ /dev/ttyUSB0 (veya ttyUSB1)
rover_teleop_node                              ───────┤
    │                                           Roboclaw 0x80 → M1, Gripper
    │   /motor_komutlari  (ROS 2 ağı)           Roboclaw 0x81 → M2, M3
    └──────────────────────────────────────►    Roboclaw 0x82 → M4, M5
```

> `/robotarm_joy`: Aynı bilgisayarda mobility joystick de çalıştığı için
> topic çakışmasını önlemek amacıyla bu proje `/joy` yerine `/robotarm_joy`
> topic'ini kullanır. Mobility `/mobility_joy` kullanır.

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

# Driver node'u başlat (varsayılan port: /dev/ttyUSB0)
ros2 launch rover_driver rover_driver.launch.py

# Port farklıysa açıkça belirt
ros2 launch rover_driver rover_driver.launch.py port_name:=/dev/ttyUSB1
```

`✅ Roboclaw CONNECTED/RECONNECTED!` mesajı çıkıyorsa bağlantı başarılıdır.

Hangi portta göründüğünü bulmak için:
```bash
ls /dev/ttyUSB*
sudo chmod 666 /dev/ttyUSBX   # X = görünen numara
```

---

### 2. Bilgisayar — Kontrol'ü başlat

Joystick'in hangi `/dev/input/jsX` cihazında göründüğünü öğren:

```bash
ls /dev/input/js*
```

Ardından başlat:

```bash
ros2 launch rover_control rover_control.launch.py joy_device:=/dev/input/js1
```

> `joy_device` parametresi **her zaman açıkça yazılmalıdır.**
> Boş bırakılırsa `joy_node` sistemdeki ilk joystick'i alır; aynı bilgisayarda
> mobility joystick de varsa yanlış cihaza bağlanabilir.

Ek seçenekler:

```bash
# Mod 1 ile başlatma
ros2 launch rover_control rover_control.launch.py joy_device:=/dev/input/js1 teleop_mode:=1

# Kalibrasyonlu başlatma
ros2 launch rover_control rover_control.launch.py joy_device:=/dev/input/js1 calibrate:=true

# Hızı düşürerek başlatma (test için)
ros2 launch rover_control rover_control.launch.py joy_device:=/dev/input/js1 motor_speed:=15000.0

# Her şey bir arada
ros2 launch rover_control rover_control.launch.py joy_device:=/dev/input/js1 teleop_mode:=1 motor_speed:=20000.0 calibrate:=true
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
ros2 launch rover_control rover_control.launch.py joy_device:=/dev/input/js1 calibrate:=true
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
Aynı anda birden fazla motoru sürmek için birden fazla butona aynı anda basılabilir.

```
Logitech Attack 3 buton düzeni (Mod 1):

  [ TRG ]  ← Boş

  [ 2 ][ 3 ]  ← M2 İleri / Geri
  [ 4 ][ 5 ]  ← M3 İleri / Geri
  [ 6 ][ 7 ]  ← M4 İleri / Geri
  [ 8 ][ 9 ]  ← M5 İleri / Geri
  [10 ][11 ]  ← M6 İleri / Geri

  Joystick Sol/Sağ    (axes[0])  ← M1
  Joystick İleri/Geri (axes[1])  ← Gripper (ileri = aç, geri = kapat)
```

---

### Mod 2 — İki Slot Seçim (varsayılan)

Önce bir motor **seçilir**, sonra joystick ile orantılı olarak kontrol edilir.
Aynı anda **2 motor birden** kontrol edilebilir:
- **Slot-A** → joystick ileri/geri (`axes[1]`)
- **Slot-B** → joystick sağa/sola (`axes[0]`)

Hız, joystick konumuna orantılıdır — tam basınca `motor_speed`, yarım basınca yarı hız.

```
Logitech Attack 3 buton düzeni (Mod 2):

  [ TRG ]  ← Boş  (buttons[0])

  [ 2 ]  ← M1 seç / bırak  (buttons[1])
  [ 3 ]  ← M2 seç / bırak  (buttons[2])
  [ 4 ]  ← M3 seç / bırak  (buttons[3])
  [ 5 ]  ← M4 seç / bırak  (buttons[4])
  [ 6 ]  ← M5 seç / bırak  (buttons[5])
  [ 7 ]  ← Gripper seç / bırak  (buttons[6])

  Joystick İleri/Geri (axes[1])  ← Slot-A'daki motoru döndürür (orantılı)
  Joystick Sol/Sağ   (axes[0])  ← Slot-B'deki motoru döndürür (orantılı)
```

**Örnek kullanım:**
1. Buton 2'ye bas → terminalde `Slot-A: M1` yazar, joystick ileri/geri M1'i döndürür
2. Buton 4'e bas → terminalde `Slot-B: M3` yazar, joystick sağa/sola M3'ü döndürür
3. Buton 2'ye tekrar bas → M1 Slot-A'dan çıkar, slot boşalır
4. İki slot doluyken yeni bir butona basarsan → `Her iki slot dolu! Once birini bosaltin.` uyarısı verir

---

## Motor — Roboclaw Bağlantı Haritası

Roboclaw kartları USB üzerinden **daisy-chain** bağlıdır, her kartın ayrı adresi vardır.
Driver'daki indeks sırası: `0:M1, 1:M2, 2:M3, 3:M4, 4:M5, 5:Gripper`

| Roboclaw Adresi | M1 Çıkışı | M2 Çıkışı |
|---|---|---|
| 0x80 (128) | M1        | Gripper   |
| 0x81 (129) | M2        | M3        |
| 0x82 (130) | M4        | M5        |

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

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| `port_name` | `/dev/ttyUSB0` | Roboclaw USB port (ör: `/dev/ttyUSB0`, `/dev/ttyUSB1`) |
| `baud_rate` | `115200` | Seri haberleşme hızı |

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

Port farklıysa önce bul:
```bash
ls /dev/ttyUSB*
```

---

**Roboclaw bağlanamıyor (`Connection Failed`):**

1. USB kablosunu kontrol et — adaptörün Jetson'a bağlı olduğundan emin ol
2. Roboclaw kartlarının güç kaynağı açık mı? Yeşil LED yanıyor mu?
3. Port numarasını kontrol et, ardından launch'a açıkça belirt:
```bash
ls -la /dev/ttyUSB*
ros2 launch rover_driver rover_driver.launch.py port_name:=/dev/ttyUSBX
```

---

**Joystick hangi js numarasında?**
```bash
ls /dev/input/js*
ros2 launch rover_control rover_control.launch.py joy_device:=/dev/input/js1
```

---

**Motor ters dönüyor:**

`rover_driver/driver_node.py` içinde ilgili `DutyM1M2` çağrısında
değerin işaretini `+`/`-` olarak değiştir, ardından tekrar build et:
```bash
cd ~/ros2_ws
colcon build --packages-select rover_driver
source install/setup.bash
```

---

**Motorlar hiç hareket etmiyor, hata da yok:**
```bash
# Teleop'tan komut geliyor mu kontrol et:
ros2 topic echo /motor_komutlari

# Joy topic'i geliyor mu kontrol et:
ros2 topic echo /robotarm_joy
```

---

**Yanlış joystick'i alıyor (mobility joystick de aynı bilgisayarda):**

`joy_device` parametresini mutlaka açıkça belirt:
```bash
ros2 launch rover_control rover_control.launch.py joy_device:=/dev/input/js1
```

Bu proje `/joy` yerine `/robotarm_joy` topic'ini kullandığı için
mobility (`/mobility_joy`) ile topic çakışması yaşanmaz; ancak `joy_node`'un
doğru fiziksel cihaza bağlandığından emin olmak için `joy_device`
her zaman belirtilmelidir.

---

**RTPS_TRANSPORT_SHM hataları:**

```
[RTPS_TRANSPORT_SHM Error] Failed init_port ...
```

Bu hatalar zararsızdır, node'lar çalışmaya devam eder. Görmek istemiyorsan:
```bash
sudo rm -rf /dev/shm/fastrtps_*
```

---

## Bağlantılı Proje

Rover hareket sistemi → [`rover_mobility`](https://github.com/busragizemyilmaz/rover_mobility)