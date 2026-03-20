# Rover Robotik Kol

Logitech Attack 3 joystick ile kontrol edilen 6 motorlu robotik kol projesi.
ROS 2 üzerinde çalışır. İki paketten oluşur: `rover_control` (joystick → komut)
ve `rover_driver` (komut → Roboclaw motor sürücüsü).

---

## Proje Yapısı

```
robotic_arm/
├── rover_arm.launch.py              ← Sistemi başlatan launch dosyası
│
├── rover_control/
│   ├── rover_control/
│   │   ├── rover_teleop_mod1.py    ← Mod 1: Çift-buton mantığı
│   │   └── rover_teleop_mod2.py    ← Mod 2: İki-slot seçim mantığı
│   ├── setup.py
│   └── package.xml
│
└── rover_driver/
    ├── rover_driver/
    │   ├── driver_node.py          ← Roboclaw USB sürücüsü
    │   └── roboclaw_3.py           ← Roboclaw kütüphanesi
    ├── setup.py
    └── package.xml
```

---

## Kurulum ve Derleme

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

## USB İzni

Roboclaw USB ile bağlanır. Her bağlantıda bir kez çalıştır:

```bash
sudo chmod 666 /dev/ttyUSB0
```

Port farklıysa bul:
```bash
ls /dev/ttyUSB*
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
ros2 launch ~/ros2_ws/src/robotic_arm/rover_arm.launch.py calibrate:=true
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

## Çalıştırma

Launch dosyası aynı anda 3 node'u birden başlatır:
`joy_node` (joystick okuma) + `rover_teleop` (komut üretme) + `rover_driver` (motor sürme)

```bash
# Normal başlatma — Mod 2, kayıtlı kalibrasyon yüklenir
ros2 launch ~/ros2_ws/src/robotic_arm/rover_arm.launch.py

# Mod 1 ile başlatma
ros2 launch ~/ros2_ws/src/robotic_arm/rover_arm.launch.py teleop_mode:=1

# Kalibrasyonlu başlatma
ros2 launch ~/ros2_ws/src/robotic_arm/rover_arm.launch.py calibrate:=true

# Hızı düşürerek başlatma (test için)
ros2 launch ~/ros2_ws/src/robotic_arm/rover_arm.launch.py motor_speed:=15000.0

# Her şey bir arada
ros2 launch ~/ros2_ws/src/robotic_arm/rover_arm.launch.py teleop_mode:=1 motor_speed:=20000.0 calibrate:=true
```

### Çalışırken hız değiştirme (node kapatmadan):
```bash
ros2 param set /rover_teleop_node motor_speed 20000.0
```

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

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| `teleop_mode` | `2` | `1` = Mod 1, `2` = Mod 2 |
| `calibrate` | `false` | `true` ise ilk joy mesajını offset olarak kaydeder |
| `motor_speed` | `30000.0` | Maksimum hız değeri (0 – 32767) |
| `axis_deadzone` | `0.15` | Joystick merkez ölü bölgesi (0.0 – 1.0) |
| `calibration_file` | `~/.ros/joystick_cal.txt` | Kalibrasyon dosyası yolu |
| `joy_device` | *(boş)* | Joystick cihaz adı, boş bırakılırsa ilk bulunan |

---

## Sık Karşılaşılan Sorunlar

**USB izin hatası:**
```bash
sudo chmod 666 /dev/ttyUSB0
```

**Joystick bulunamıyor:**
```bash
ls /dev/input/js*
# Çıktıya göre:
ros2 launch ... joy_device:=js1
```

**Motor ters dönüyor:**
`rover_driver/driver_node.py` içinde ilgili `DutyM1M2` çağrısında
değerin işaretini `+`/`-` olarak değiştir.

**Motorlar hiç hareket etmiyor, hata da yok:**
```bash
# Teleop'tan komut geliyor mu kontrol et:
ros2 topic echo /motor_komutlari
```
