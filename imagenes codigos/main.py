# main.py

import os
import time
import argparse
import subprocess
import webbrowser

try:
    import cv2
    import numpy as np
    import pyautogui
    import pygetwindow as gw
except ModuleNotFoundError as exc:
    raise SystemExit(
        f"Falta instalar '{exc.name}'. Ejecuta: python -m pip install -r requirements.txt"
    ) from exc

try:
    from pyautogui import ImageNotFoundException
except ImportError:
    from pyscreeze import ImageNotFoundException

pyautogui.PAUSE = 0

# ——————————————————————————————————————————
#   CONFIGURACIÓN DE RUTAS A IMÁGENES
# ——————————————————————————————————————————
SCRIPT_DIR            = os.path.dirname(os.path.abspath(__file__))
REGISTRAR_IMG         = os.path.join(SCRIPT_DIR, 'registrar_button.png')
SUBMIT_IMG            = os.path.join(SCRIPT_DIR, 'submit_button.png')
INVALID_POPUP_IMG     = os.path.join(SCRIPT_DIR, 'error_popup.png')

# buscamos el popup de codigo ya registrado
for name in ('new_code_already_register', 'new_code_alredy_register', 'duplicate_popup'):
    for ext in ('png', 'PNG'):
        _dup = os.path.join(SCRIPT_DIR, f'{name}.{ext}')
        if os.path.exists(_dup):
            DUPLICATE_POPUP_IMG = _dup
            break
    else:
        continue
    break
else:
    raise FileNotFoundError("No encontre popup de codigo ya registrado.")

# buscamos el boton OK/Aceptar del popup
for name in ('new_accept_button', 'error_accept_button', 'ACCEPT_BUTTON_IMG'):
    for ext in ('png', 'PNG'):
        _acc = os.path.join(SCRIPT_DIR, f'{name}.{ext}')
        if os.path.exists(_acc):
            ACCEPT_BUTTON_IMG = _acc
            break
    else:
        continue
    break
else:
    raise FileNotFoundError("No encontre boton Aceptar.")

# buscamos success_popup.png o .PNG (opcional)
SUCCESS_POPUP_IMG = None
for ext in ('png', 'PNG'):
    _succ = os.path.join(SCRIPT_DIR, f'success_popup.{ext}')
    if os.path.exists(_succ):
        SUCCESS_POPUP_IMG = _succ
        break

def _existing_images(*names):
    found = []
    seen = set()
    for name in names:
        root, ext = os.path.splitext(name)
        candidates = [name] if ext else [f"{name}.png", f"{name}.PNG"]
        for candidate in candidates:
            path = os.path.join(SCRIPT_DIR, candidate)
            key = os.path.normcase(os.path.abspath(path))
            if os.path.exists(path) and key not in seen:
                seen.add(key)
                found.append(path)
    return found

DUPLICATE_POPUP_IMAGES = _existing_images(
    'new_code_already_register',
    'new_code_alredy_register',
    'duplicate_popup',
)
INVALID_POPUP_IMAGES = _existing_images('new_invalid_code', 'error_popup')
ACCEPT_BUTTON_IMAGES = _existing_images(
    'new_accept_button',
    'error_accept_button',
    'ACCEPT_BUTTON_IMG',
)
SUCCESS_POPUP_IMAGES = _existing_images('success_popup')

if not DUPLICATE_POPUP_IMAGES:
    raise FileNotFoundError("No encontre imagen para codigo ya registrado.")
if not INVALID_POPUP_IMAGES:
    raise FileNotFoundError("No encontre imagen para codigo invalido.")
if not ACCEPT_BUTTON_IMAGES:
    raise FileNotFoundError("No encontre imagen del boton Aceptar.")

DUPLICATE_POPUP_IMG = DUPLICATE_POPUP_IMAGES[0]
INVALID_POPUP_IMG = INVALID_POPUP_IMAGES[0]
ACCEPT_BUTTON_IMG = ACCEPT_BUTTON_IMAGES[0]
SUCCESS_POPUP_IMG = SUCCESS_POPUP_IMAGES[0] if SUCCESS_POPUP_IMAGES else None

PAGE_LOAD_SECONDS = 8
POPUP_TEXT_CONFIDENCE = 0.72
LOW_POPUP_TEXT_CONFIDENCE = 0.45
HIGH_POPUP_TEXT_CONFIDENCE = 0.92
POPUP_INITIAL_DELAY_SECONDS = 0.8
ACCEPT_BUTTON_CONFIDENCE = 0.75
_GRAY_TEMPLATE_CACHE = {}
_MESSAGE_TEMPLATE_CACHE = {}
CONTROL_WINDOW_TITLE = None

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

def remember_control_window():
    global CONTROL_WINDOW_TITLE
    try:
        win = gw.getActiveWindow()
    except Exception:
        win = None
    if win and win.title:
        CONTROL_WINDOW_TITLE = win.title

def _activate_window_with_title(title, timeout=5):
    if not title:
        return False
    t0 = time.time()
    while time.time() - t0 < timeout:
        wins = gw.getWindowsWithTitle(title)
        if wins:
            win = wins[0]
            if win.isMinimized:
                win.restore()
            try:
                win.activate()
                time.sleep(0.5)
                return True
            except Exception:
                pass
        time.sleep(0.25)
    return False

def focus_control_window():
    if _activate_window_with_title(CONTROL_WINDOW_TITLE, timeout=3):
        return True

    fallback_titles = (
        "Visual Studio Code",
        "Visual Studio",
        "MINGW64",
        "Git Bash",
        "PowerShell",
        "Command Prompt",
    )
    for title in fallback_titles:
        if _activate_window_with_title(title, timeout=1):
            return True
    return False

def _find_brave_exe():
    candidates = [
        os.environ.get("BRAVE_PATH"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None

def _activate_brave(timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        wins = gw.getWindowsWithTitle("Brave")
        if wins:
            win = wins[0]
            if win.isMinimized:
                win.restore()
            try:
                win.maximize()
            except Exception:
                pass
            win.activate()
            time.sleep(1)
            return True
        time.sleep(0.5)
    return False

def open_brave_and_go(url):
    brave_exe = _find_brave_exe()
    if brave_exe:
        subprocess.Popen([brave_exe, "--new-window", url])
        print(f"[INFO] Abriendo Brave: {url}")
    else:
        print("[WARN] No encontre brave.exe. Abriendo la URL con el navegador predeterminado.")
        webbrowser.open(url, new=1)

    if not _activate_brave(timeout=20):
        raise RuntimeError("No pude activar Brave despues de abrir la URL.")
    pyautogui.hotkey('ctrl', '0')
    time.sleep(PAGE_LOAD_SECONDS)

def _save_debug_screenshot(label):
    safe_label = "".join(ch if ch.isalnum() else "_" for ch in label)
    path = os.path.join(SCRIPT_DIR, f"debug_{safe_label}_{int(time.time())}.png")
    pyautogui.screenshot(path)
    return path

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
    screenshot_path = _save_debug_screenshot(os.path.basename(img_path))
    raise TimeoutError(
        f"Timeout esperando {os.path.basename(img_path)} en pantalla. "
        f"Captura guardada en: {screenshot_path}"
    )

def click_registrar_codigos():
    btn = _wait_and_locate_center(REGISTRAR_IMG, confidence=0.6, grayscale=True, timeout=30)
    pyautogui.click(btn)
    time.sleep(2)

def click_accept():
    """
    Clica repetidamente el botón "Aceptar/OK" hasta que desaparezca el popup.
    Devuelve True si clicó algo; False si no encontró el botón.
    """
    if not ACCEPT_BUTTON_IMAGES:
        return False
    start = time.time()
    clicked = False
    while time.time() - start < 10:
        loc = None
        for img_path in ACCEPT_BUTTON_IMAGES:
            try:
                loc = pyautogui.locateCenterOnScreen(
                    img_path,
                    confidence=ACCEPT_BUTTON_CONFIDENCE,
                    grayscale=True,
                )
            except (ImageNotFoundException, OSError):
                loc = None
            if loc:
                break
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

def _popup_present_any(img_paths, confidence=0.6, grayscale=True):
    for img_path in img_paths:
        if _popup_present(img_path, confidence=confidence, grayscale=grayscale):
            return img_path
    return None

def _screenshot_gray():
    screenshot = pyautogui.screenshot()
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)

def _read_gray_template(img_path):
    if img_path not in _GRAY_TEMPLATE_CACHE:
        image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise FileNotFoundError(img_path)
        _GRAY_TEMPLATE_CACHE[img_path] = image
    return _GRAY_TEMPLATE_CACHE[img_path]

def _message_template(img_path):
    if img_path in _MESSAGE_TEMPLATE_CACHE:
        return _MESSAGE_TEMPLATE_CACHE[img_path]

    image = _read_gray_template(img_path)
    h, w = image.shape[:2]
    band = image[int(h * 0.48):int(h * 0.72), int(w * 0.08):int(w * 0.92)]
    mask = band < 245
    ys, xs = np.where(mask)

    if len(xs) == 0:
        template = band
    else:
        pad = 6
        y1 = max(0, int(ys.min()) - pad)
        y2 = min(band.shape[0], int(ys.max()) + pad + 1)
        x1 = max(0, int(xs.min()) - pad)
        x2 = min(band.shape[1], int(xs.max()) + pad + 1)
        template = band[y1:y2, x1:x2]

    _MESSAGE_TEMPLATE_CACHE[img_path] = template
    return template

def _match_score(haystack_gray, template_gray):
    h, w = template_gray.shape[:2]
    if haystack_gray.shape[0] < h or haystack_gray.shape[1] < w:
        return 0.0
    result = cv2.matchTemplate(haystack_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    return float(result.max())

def _best_popup_score(screenshot_gray, img_paths):
    best_score = 0.0
    best_path = None
    for img_path in img_paths:
        score = _match_score(screenshot_gray, _message_template(img_path))
        if score > best_score:
            best_score = score
            best_path = img_path
    return best_score, best_path

def _format_popup_scores(scores):
    return " | ".join(f"{name}={score:.3f}" for name, score in scores.items())

def _choose_popup_type(scores, min_confidence):
    duplicate_score = scores.get('duplicate', 0.0)
    invalid_score = scores.get('invalid', 0.0)
    success_score = scores.get('success', 0.0)

    if max(duplicate_score, invalid_score) >= min_confidence:
        if duplicate_score >= invalid_score:
            return 'duplicate'
        return 'invalid'

    if success_score >= min_confidence:
        return 'success'

    return None

def classify_popup(timeout=8, poll=0.25):
    best_scores = {'duplicate': 0.0, 'invalid': 0.0, 'success': 0.0}
    accept_seen_at = None

    time.sleep(POPUP_INITIAL_DELAY_SECONDS)
    t0 = time.time()
    while time.time() - t0 < timeout:
        accept_visible = _popup_present_any(
            ACCEPT_BUTTON_IMAGES,
            confidence=ACCEPT_BUTTON_CONFIDENCE,
            grayscale=True,
        )
        screenshot_gray = _screenshot_gray()
        duplicate_score, _ = _best_popup_score(screenshot_gray, DUPLICATE_POPUP_IMAGES)
        invalid_score, _ = _best_popup_score(screenshot_gray, INVALID_POPUP_IMAGES)
        success_score = 0.0
        if SUCCESS_POPUP_IMAGES:
            success_score, _ = _best_popup_score(screenshot_gray, SUCCESS_POPUP_IMAGES)

        scores = {
            'duplicate': duplicate_score,
            'invalid': invalid_score,
            'success': success_score,
        }
        for status, score in scores.items():
            best_scores[status] = max(best_scores[status], score)

        if accept_visible:
            if accept_seen_at is None:
                accept_seen_at = time.time()
            elif time.time() - accept_seen_at >= 0.4:
                popup_type = _choose_popup_type(scores, POPUP_TEXT_CONFIDENCE)
                if popup_type:
                    return popup_type, scores

            if time.time() - accept_seen_at >= 1.5:
                popup_type = _choose_popup_type(scores, LOW_POPUP_TEXT_CONFIDENCE)
                if popup_type:
                    return popup_type, scores
                return 'success', scores
        else:
            accept_seen_at = None
            popup_type = _choose_popup_type(scores, HIGH_POPUP_TEXT_CONFIDENCE)
            if popup_type:
                return popup_type, scores

        time.sleep(poll)

    return None, best_scores

def save_already_registered_report(codes):
    if not codes:
        print("[INFO] No se detectaron codigos ya registrados.")
        return None

    unique_codes = list(dict.fromkeys(codes))
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCRIPT_DIR, f"codigos_ya_registrados_{stamp}.txt")
    with open(path, "w", encoding="utf-8") as f:
        for code in unique_codes:
            f.write(f"{code}\n")

    print(f"[INFO] Codigos ya registrados guardados en: {path}")
    print(f"[INFO] Total detectados: {len(codes)} | Unicos: {len(unique_codes)}")
    return path

def save_invalid_codes_report(codes):
    if not codes:
        print("[INFO] No se detectaron codigos invalidos.")
        return None

    unique_codes = list(dict.fromkeys(codes))
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCRIPT_DIR, f"codigos_invalidos_{stamp}.txt")
    with open(path, "w", encoding="utf-8") as f:
        for code in unique_codes:
            f.write(f"{code}\n")

    print(f"[INFO] Codigos invalidos guardados en: {path}")
    print(f"[INFO] Total invalidos: {len(codes)} | Unicos: {len(unique_codes)}")
    return path

def send_code(code):
    # 1) localizar ✔
    btn = _wait_and_locate_center(SUBMIT_IMG, confidence=0.6, grayscale=True, timeout=30)

    # 2) calcular y clicar el campo de texto
    x, y = btn.x - INPUT_OFFSET_X, btn.y
    pyautogui.click(x, y)
    time.sleep(0.15)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    time.sleep(0.05)

    # 3) teclear el código
    print(f"[TRY]  {code}")
    pyautogui.typewrite(code, interval=0.005)
    time.sleep(0.2)

    # 4) clicar ✔ para enviar
    pyautogui.click(btn)

    popup_type, scores = classify_popup(timeout=8, poll=0.25)

    if popup_type == 'duplicate':
        click_accept()
        print(f"[SKIP] Codigo ya registrado: {code} ({_format_popup_scores(scores)})")
        return 'duplicate'

    if popup_type == 'invalid':
        click_accept()
        print(f"[ERROR] Codigo invalido: {code} ({_format_popup_scores(scores)})")
        return 'invalid'

    if popup_type == 'success':
        if click_accept():
            print(f"[OK]   {code}  (success con alerta)")
        else:
            print(f"[OK]   {code}  (success)")
        time.sleep(0.7)
        return 'success'

    print(f"[OK]   {code}  (sin popup claro: {_format_popup_scores(scores)})")
    return 'success'

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

    remember_control_window()
    open_brave_and_go(args.url)
    click_registrar_codigos()
    time.sleep(5)

    already_registered_codes = []
    invalid_codes = []
    try:
        for code in codes:
            status = send_code(code)
            if status == 'duplicate':
                already_registered_codes.append(code)
            elif status == 'invalid':
                invalid_codes.append(code)
    finally:
        save_already_registered_report(already_registered_codes)
        save_invalid_codes_report(invalid_codes)

if __name__ == "__main__":
    main()



"""
python main.py mis_codigos.txt https://aditivosqualitor.com/CO/Private-site/
"""
