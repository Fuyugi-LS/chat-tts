<div align="center">

<img src="assets/icon.ico" alt="tdibam_t2s icon" width="128" height="128">

# tdibam_t2s (YouTube Chat TTS)

**ระบบอ่านแชท YouTube Live อัตโนมัติด้วย Edge TTS (Native PyQt6)**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey?style=flat-square&logo=windows&logoColor=white)]()

> ดึงแชท YouTube Live แบบ Real-time แล้วแปลงข้อความเป็นเสียง (PCM)
</div>

---

## ✨ Features
-  **Standalone Installer:** มาพร้อมตัวติดตั้ง `.exe` (สร้างจาก NSIS) ติดตั้งง่ายเหมือนโปรแกรมทั่วไป
-  **Smart Logging:** ระบบจัดเก็บ Log อัตโนมัติ (แยกตาม Session) และลบ Log เก่าทิ้งให้อัตโนมัติ (30 วัน)

---

## 📦 Installation & Usage

### วิธีที่ 1: ติดตั้งผ่าน Installer (สำหรับผู้ใช้งานทั่วไป - แนะนำ)
1. ไปที่โฟลเดอร์ `dist/` หรือหน้า Releases
2. รันไฟล์ `tdibam_t2s-1.0.0-setup.exe`
3. เปิดโปรแกรมผ่าน Shortcut บน Desktop หรือ Start Menu

### วิธีที่ 2: รันจาก Source Code (สำหรับนักพัฒนา)
```batch
# 1. โคลนโปรเจกต์
git clone [https://github.com/your-username/tdibam_t2s.git](https://github.com/your-username/tdibam_t2s.git)
cd tdibam_t2s

# 2. ติดตั้ง Dependencies (แนะนำให้ใช้ Virtual Environment)
pip install -r requirements.txt

# 3. รันโปรแกรม
python tt2s.py
```

---

## 🎮 How to Use (วิธีใช้งาน)

1. เปิดโปรแกรม `tdibam_t2s`
2. นำลิงก์ **YouTube Live** หรือ **Video ID** มาใส่ในช่อง `YouTube Video ID / URL`
*(ตัวอย่าง: `https://youtube.com/watch?v=fiss3CP8-BY` หรือแค่ `fiss3CP8-BY`)*
3. ตั้งค่าการหน่วงเวลา:
* **Delay per char:** หน่วงเวลาตามจำนวนตัวอักษร (ค่าเริ่มต้น: 0.03 วินาที)
* **Max delay:** ลิมิตเวลาหน่วงสูงสุดเพื่อไม่ให้เสียงขาดช่วงนานเกินไป (ค่าเริ่มต้น: 2.0 วินาที)
4. กด **Save** เพื่อบันทึกการตั้งค่าลง Session
5. กด **Start** เพื่อเริ่มอ่านแชท!
6. สามารถกดปิดกากบาทที่หน้าต่างเพื่อพับเก็บโปรแกรมลง **System Tray (มุมขวาล่าง)** ได้ โปรแกรมจะยังทำงานอยู่เบื้องหลัง

---

## 🏗️ Architecture & โครงสร้างการทำงาน

โปรเจกต์นี้ถูกออกแบบมาแบบ **Decoupled Architecture** เพื่อให้แต่ละส่วนทำงานแยกกันอย่างอิสระ:

```text
tt2s/
├── tt2s.py           # Entry Point (ตัวบูตระบบ, จัดการ Signal และ Log)
├── src/
│   ├── config.py     # ตัวจัดการ Defaults และ Extract Video ID ด้วย Regex
│   ├── tt2s_gui.py   # Pure GUI Layer (PyQt6) - ไม่มี Business logic ปน
│   ├── worker.py     # Background Thread (QThread + Asyncio) ดึงแชทและเล่นเสียง
│   └── notif_popup.py# Subprocess แจ้งเตือน (Frameless Window พร้อม Animation)
└─── installer/        # สคริปต์สำหรับแพ็กเกจ .exe ด้วย PyInstaller และ NSIS
```

### Flow การทำงานหลัก:

1. **Input:** `worker.py` เชื่อมต่อ YouTube Live ผ่าน `pytchat`
2. **Queueing:** เมื่อมีแชทใหม่ จะถูกส่งเข้า `queue.Queue` แบบ Thread-safe
3. **Generation:** `edge-tts` ดึงข้อความจากคิวไปสังเคราะห์เป็น `raw-24khz-16bit-mono-pcm` (ทำใน Memory 100%)
4. **Playback:** ข้อมูล PCM จะถูกแปลงเป็น Float32 ผ่าน `numpy` และส่งเข้า Audio Stream ของ `sounddevice` เพื่อเล่นออกลำโพงทันที

---

## 🛠️ Building the Executable (วิธี Build โปรแกรม)

โปรเจกต์นี้ใช้ `PyInstaller` สำหรับแพ็กโค้ด Python และ `NSIS` สำหรับทำตัวติดตั้ง

```bash
# ฝั่ง Windows (PowerShell/CMD)
cd installer
build.bat
# หรือ
./build.ps1
```

ไฟล์ติดตั้งที่เสร็จสมบูรณ์จะอยู่ในโฟลเดอร์ `dist/`

---

## 📝 Dependencies

* `PySide6` (>=6.11.0) - GUI Framework
* `edge-tts` (==7.2.8) - Microsoft Edge TTS Engine
* `pytchat` (==0.5.5) - YouTube Live Chat scraper
* `sounddevice` (>=0.4.0) - Audio playback
* `numpy` (>=1.24.0) - Audio buffer processing

## LICENSE
For license, see LICENSE.md
