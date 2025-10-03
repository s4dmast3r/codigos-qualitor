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
SCRIPT_DIR            = os.path.dirname(os.path.abspath(__file__))
REGISTRAR_IMG         = os.path.join(SCRIPT_DIR, 'registrar_button.png')
SUBMIT_IMG            = os.path.join(SCRIPT_DIR, 'submit_button.png')
INVALID_POPUP_IMG     = os.path.join(SCRIPT_DIR, 'error_popup.png')

# buscamos duplicate_popup.png o duplicate_popup.PNG
for ext in ('png', 'PNG'):
    _dup = os.path.join(SCRIPT_DIR, f'duplicate_popup.{ext}')
    if os.path.exists(_dup):
        DUPLICATE_POPUP_IMG = _dup
        break
else:
    raise FileNotFoundError("No encontré duplicate_popup.png/PNG")

# buscamos error_accept_button.png o .PNG (el botón OK/Aceptar del popup)
for ext in ('png', 'PNG'):
    _acc = os.path.join(SCRIPT_DIR, f'error_accept_button.{ext}')
    if os.path.exists(_acc):
        ACCEPT_BUTTON_IMG = _acc
        break
else:
    raise FileNotFoundError("No encontré error_accept_button.png/PNG")

# buscamos success_popup.png o .PNG (opcional)
SUCCESS_POPUP_IMG = None
for ext in ('png', 'PNG'):
    _succ = os.path.join(SCRIPT_DIR, f'success_popup.{ext}')
    if os.path.exists(_succ):
        SUCCESS_POPUP_IMG = _succ
        break

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
    pyautogui.hotkey('ctrl', 't')
    time.sleep(0.5)
    pyautogui.typewrite(url, interval=0.02)
    pyautogui.press('enter')
    time.sleep(3)

def _wait_and_locate_center(img_path, confidence=0.6, grayscale=True, timeout=15, poll=0.3):
    """Espera hasta que una imagen aparezca en pantalla y devuelve su centro."""
    if not os.path.exists(img_path):
        raise FileNotFoundError(img_path)
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            loc = pyautogui.locateCenterOnScreen(img_path, confidence=confidence, grayscale=grayscale)
        except (ImageNotFoundException, OSError):
            loc = None
        if loc:
            return loc
        time.sleep(poll)
    raise TimeoutError(f"Timeout esperando {os.path.basename(img_path)} en pantalla.")

def click_registrar_codigos():
    btn = _wait_and_locate_center(REGISTRAR_IMG, confidence=0.6, grayscale=True, timeout=30)
    pyautogui.click(btn)
    time.sleep(2)

def click_accept():
    """
    Clica repetidamente el botón "Aceptar/OK" hasta que desaparezca el popup.
    Devuelve True si clicó algo; False si no encontró el botón.
    """
    if not os.path.exists(ACCEPT_BUTTON_IMG):
        return False
    start = time.time()
    clicked = False
    while time.time() - start < 10:
        try:
            loc = pyautogui.locateCenterOnScreen(ACCEPT_BUTTON_IMG, confidence=0.6, grayscale=True)
        except (ImageNotFoundException, OSError):
            loc = None
        if loc:
            pyautogui.click(loc)
            clicked = True
            time.sleep(0.5)
        else:
            break
    return clicked

def _popup_present(img_path, confidence=0.6, grayscale=True):
    try:
        return pyautogui.locateOnScreen(img_path, confidence=confidence, grayscale=grayscale) is not None
    except Exception:
        return False

def send_code(code):
    # 1) localizar ✔
    btn = _wait_and_locate_center(SUBMIT_IMG, confidence=0.6, grayscale=True, timeout=30)

    # 2) calcular y clicar el campo de texto
    x, y = btn.x - INPUT_OFFSET_X, btn.y
    pyautogui.click(x, y)
    time.sleep(0.2)

    # 3) teclear el código
    pyautogui.typewrite(code, interval=0.01)
    time.sleep(0.2)

    # 4) clicar ✔ para enviar
    pyautogui.click(btn)

    # 5) esperar aparición de popup (duplicate / invalid / success)
    t0 = time.time()
    popup_type = None
    while time.time() - t0 < 6:  # margen extra por alert nativo
        # duplicado
        if _popup_present(DUPLICATE_POPUP_IMG, confidence=0.6, grayscale=True):
            popup_type = 'duplicate'
            break
        # inválido
        if _popup_present(INVALID_POPUP_IMG, confidence=0.6, grayscale=True):
            popup_type = 'invalid'
            break
        # success por imagen dedicada (si existe)
        if SUCCESS_POPUP_IMG and _popup_present(SUCCESS_POPUP_IMG, confidence=0.6, grayscale=True):
            popup_type = 'success'
            break
        # success genérico: ver si el botón OK está en pantalla
        if _popup_present(ACCEPT_BUTTON_IMG, confidence=0.6, grayscale=True):
            popup_type = 'success'
            break

        time.sleep(0.25)

    # 6) manejar popup
    if popup_type == 'duplicate':
        click_accept()
        print(f"[SKIP] Código ya registrado: {code}")
        return

    elif popup_type == 'invalid':
        click_accept()
        print(f"[ERROR] Código inválido: {code}")
        input("⚠️  Corrige manualmente y pulsa Enter para continuar…")
        return

    elif popup_type == 'success':
        if click_accept():
            print(f"[OK]   {code}  (success con alerta)")
        else:
            print(f"[OK]   {code}  (success)")
        time.sleep(0.7)
        return

    # 7) si no hubo popup (flujo anterior)
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