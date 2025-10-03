# main.py

import os
import time
import argparse

import pyautogui
import pygetwindow as gw
from pyautogui import ImageNotFoundException

# ——————————————————————————————————————————
#   CONFIGURACIÓN DE RUTAS A IMÁGENES
# ——————————————————————————————————————————
SCRIPT_DIR           = os.path.dirname(os.path.abspath(__file__))
REGISTRAR_IMG        = os.path.join(SCRIPT_DIR, 'registrar_button.png')
SUBMIT_IMG           = os.path.join(SCRIPT_DIR, 'submit_button.png')
INVALID_POPUP_IMG    = os.path.join(SCRIPT_DIR, 'error_popup.png')
# buscamos duplicate_popup.png o duplicate_popup.PNG
for ext in ('png','PNG'):
    _dup = os.path.join(SCRIPT_DIR, f'duplicate_popup.{ext}')
    if os.path.exists(_dup):
        DUPLICATE_POPUP_IMG = _dup
        break
else:
    raise FileNotFoundError("No encontré duplicate_popup.png/PNG")
# buscamos error_accept_button.png o .PNG
for ext in ('png','PNG'):
    _acc = os.path.join(SCRIPT_DIR, f'error_accept_button.{ext}')
    if os.path.exists(_acc):
        ACCEPT_BUTTON_IMG = _acc
        break
else:
    raise FileNotFoundError("No encontré error_accept_button.png/PNG")

INPUT_OFFSET_X = 250  # px a la izquierda del botón ✔ para el campo de texto

# ——————————————————————————————————————————
#   FUNCIONES AUXILIARES
# ——————————————————————————————————————————
def load_codes(path):
    with open(path, encoding='utf-8') as f:
        return [line.strip().split(',')[0] for line in f if line.strip()]

def focus_brave(title="Brave"):
    wins = gw.getWindowsWithTitle(title)
    if not wins:
        raise RuntimeError(f"No encontré ventana con título '{title}'")
    wins[0].activate()
    time.sleep(1)

def open_tab_and_go(url):
    pyautogui.hotkey('ctrl','t')
    time.sleep(0.5)
    pyautogui.typewrite(url, interval=0.02)
    pyautogui.press('enter')
    time.sleep(3)

def click_registrar_codigos():
    if not os.path.exists(REGISTRAR_IMG):
        raise FileNotFoundError(REGISTRAR_IMG)
    btn = None
    while btn is None:
        try:
            btn = pyautogui.locateCenterOnScreen(REGISTRAR_IMG, confidence=0.6, grayscale=True)
        except (ImageNotFoundException, OSError):
            btn = None
        time.sleep(0.3)
    pyautogui.click(btn)
    time.sleep(2)

def click_accept():
    """
    Clica repetidamente el botón "Aceptar" hasta que desaparezca el popup.
    """
    if not os.path.exists(ACCEPT_BUTTON_IMG):
        return
    start = time.time()
    while time.time() - start < 10:
        loc = None
        try:
            loc = pyautogui.locateCenterOnScreen(ACCEPT_BUTTON_IMG, confidence=0.6, grayscale=True)
        except (ImageNotFoundException, OSError):
            loc = None
        if loc:
            pyautogui.click(loc)
            time.sleep(0.5)
        else:
            break

def send_code(code):
    # 1) localizar ✔
    if not os.path.exists(SUBMIT_IMG):
        raise FileNotFoundError(SUBMIT_IMG)
    btn = None
    while btn is None:
        try:
            btn = pyautogui.locateCenterOnScreen(SUBMIT_IMG, confidence=0.6, grayscale=True)
        except (ImageNotFoundException, OSError):
            btn = None
        time.sleep(0.3)

    # 2) calcular y clicar el campo de texto
    x, y = btn.x - INPUT_OFFSET_X, btn.y
    pyautogui.click(x, y)
    time.sleep(0.2)

    # 3) teclear el código
    pyautogui.typewrite(code, interval=0.01)
    time.sleep(0.2)

    # 4) clicar ✔ para enviar
    pyautogui.click(btn)

    # 5) esperar aparición de popup
    t0 = time.time()
    popup_type = None
    while time.time() - t0 < 3:
        # chequea duplicado
        try:
            if pyautogui.locateOnScreen(DUPLICATE_POPUP_IMG, confidence=0.6, grayscale=True):
                popup_type = 'duplicate'
                break
        except Exception:
            pass
        # chequea inválido
        try:
            if pyautogui.locateOnScreen(INVALID_POPUP_IMG, confidence=0.6, grayscale=True):
                popup_type = 'invalid'
                break
        except Exception:
            pass
        time.sleep(0.3)

    # 6) manejar popup
    if popup_type == 'duplicate':
        click_accept()  # repetidamente hasta cerrar
        print(f"[SKIP] Código ya registrado: {code}")
        return

    elif popup_type == 'invalid':
        click_accept()
        print(f"[ERROR] Código inválido: {code}")
        input("⚠️  Corrige manualmente y pulsa Enter para continuar…")
        return

    # 7) si no hubo popup
    time.sleep(3)
    print(f"[OK]   {code}")

def main():
    parser = argparse.ArgumentParser(
        description="Bot PyAutoGUI para registrar códigos en Qualitor usando Brave"
    )
    parser.add_argument("codes_file", help=".txt o .csv con los códigos")
    parser.add_argument("url",        help="URL de la página inicial")
    args = parser.parse_args()

    codes = load_codes(args.codes_file)
    if not codes:
        print("❌ No hay códigos para enviar.")
        return

    focus_brave("Brave")
    open_tab_and_go(args.url)

    time.sleep(5)
    click_registrar_codigos()
    time.sleep(5)

    for code in codes:
        send_code(code)

if __name__ == "__main__":
    main()




"""
python main.py mis_codigos.txt https://aditivosqualitor.com/Private-site/
"""