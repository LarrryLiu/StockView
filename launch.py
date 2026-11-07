"""Start the public viewer on loopback only. / 仅在本机启动公开查看器。"""

import argparse
import threading
import webbrowser

from werkzeug.serving import make_server
from viewer import app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = make_server("127.0.0.1", 5051, app, threaded=True)
    if not args.no_browser:
        opener = threading.Timer(0.5, webbrowser.open_new_tab, args=("http://127.0.0.1:5051/",))
        opener.daemon = True
        opener.start()
    print("Open http://127.0.0.1:5051/ — Ctrl+C to stop. / 按 Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
