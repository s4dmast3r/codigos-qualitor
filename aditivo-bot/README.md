# AditivoBot

Prototipo mínimo para automatizar la lectura OCR de stickers y la redención automática en la página de aditivosqualitor.com.

Este repo incluye:

* **bot.py** – Host nativo + OCR + cola SQLite.
* **requirements.txt** – Dependencias de Python.
* **native.json** – Descriptor para registrarlo como Native Messaging Host en Chrome/Brave.
* **extension/** – Extensión Manifest V3 que recibe códigos vía Native Messaging y los pega en la web.
* **bandeja.stl** – Modelo 3‑D de la bandeja 5× (demo genérico).
