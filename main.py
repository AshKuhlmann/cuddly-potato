import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pdfnotebook.webapp import app

if __name__ == "__main__":
    host = os.environ.get("PDFNOTEBOOK_HOST", "0.0.0.0")
    port = int(os.environ.get("PDFNOTEBOOK_PORT", "5050"))
    
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        print(f" * LAN Access: http://{ip}:{port}/test-ui")
    except Exception:
        print(" * Could not determine LAN IP")

    app.run(host=host, port=port)
