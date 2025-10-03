
#!/usr/bin/env python3
"""Host nativo + OCR mínimo (modo --mock para pruebas)."""
import argparse, json, sys, time, random
def send(obj):
    data = json.dumps(obj).encode('utf-8')
    sys.stdout.buffer.write(len(data).to_bytes(4,'little'))
    sys.stdout.buffer.write(data)
    sys.stdout.flush()
def mock():
    codes = [f"B-DEMO{n:04d}" for n in range(3)]
    for c in codes:
        send({"code": c})
        time.sleep(1)
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()
    if args.mock:
        mock()
