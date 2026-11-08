"""Start the public viewer on loopback only. / 仅在本机启动公开查看器。"""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import webbrowser

from werkzeug.serving import make_server


def prepare_private_source(private_root, config, input_dir=None):
    """Delegate computation to an authorized private checkout.

    将策略计算委托给已获授权的私有仓库本地副本。
    """
    root = Path(private_root).expanduser().resolve()
    bridge = root / "viewer_bridge.py"
    if not bridge.is_file():
        raise ValueError("Private checkout is missing viewer_bridge.py. / 缺少私有策略入口。")
    config = Path(config).expanduser().resolve()
    if not config.is_file():
        raise ValueError("Private configuration file is missing. / 缺少私有配置文件。")
    exports = root / ".viewer-exports"
    exports.mkdir(exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix="run-", dir=exports))
    command = [sys.executable, str(bridge), "--config", str(config), "--destination", str(destination)]
    if input_dir:
        command.extend(["--input", str(Path(input_dir).expanduser().resolve())])
    subprocess.run(command, cwd=root, check=True)
    if not (destination / "picks.json").is_file() or not (destination / "daily").is_dir():
        raise ValueError("Private engine did not return viewer data. / 私有引擎未返回图表数据。")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--private-root", type=Path, help="Authorized local private checkout / 已授权私有仓库路径")
    parser.add_argument("--private-config", type=Path, help="Private configuration / 私有配置文件")
    parser.add_argument("--private-input", type=Path, help="Optional private data directory / 可选私有数据目录")
    args = parser.parse_args()
    if args.private_root:
        if not args.private_config:
            parser.error("--private-root requires --private-config")
        try:
            destination = prepare_private_source(args.private_root, args.private_config, args.private_input)
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            parser.exit(1, f"Private engine failed; viewer was not started. / 私有引擎失败，未启动查看器。\n{exc}\n")
        os.environ["STOCKVIEW_DATA_DIR"] = str(destination / "daily")
        os.environ["STOCKVIEW_PICKS_FILE"] = str(destination / "picks.json")
        os.environ["STOCKVIEW_PRIVATE_MODE"] = "1"
    elif args.private_config or args.private_input:
        parser.error("Private options require --private-root")
    from viewer import app

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
