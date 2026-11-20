"""Colabで生成する場合の起動入口。Windowsではパスワードを * で表示。"""
import os
import runpy
import sys
from getpass import getpass
from pathlib import Path


def masked_password(prompt):
    """Windowsの端末で文字を伏せ、入力・削除を表示に反映する。"""
    if os.name != "nt":
        return getpass(prompt)
    import msvcrt

    if not sys.stdin.isatty():
        raise RuntimeError("VS Codeのターミナルまたはコマンドプロンプトで実行してください。")
    print(prompt, end="", flush=True)
    chars = []
    while True:
        char = msvcrt.getwch()
        if char in ("\r", "\n"):
            print()
            return "".join(chars)
        if char == "\x03":
            print()
            raise KeyboardInterrupt
        if char in ("\x00", "\xe0"):
            msvcrt.getwch()  # 矢印キーなどの特殊キーを無視する。
            continue
        if char == "\b":
            if chars:
                chars.pop()
                print("\b \b", end="", flush=True)
        elif char == "\x15":  # Ctrl+Uで全消去
            print("\b \b" * len(chars), end="", flush=True)
            chars.clear()
        elif char.isprintable():
            chars.append(char)
            print("*", end="", flush=True)


def main():
    print("先にcolab/RealFace_Colab_Server.ipynbで受付サーバーを起動してください。")
    os.environ["REALFACE_COLAB_URL"] = input("Colabの公開URL：https://...gradio.live → ").strip()
    os.environ["REALFACE_COLAB_USER"] = "realface"
    print("パスワードは * で表示されます（Windows）。Enterで確定、Backspaceで削除、Ctrl+Uで全消去。")
    while True:
        password = masked_password("Colabで設定したパスワード：")
        if password:
            break
        print("パスワードを入力してください。")
    os.environ["REALFACE_COLAB_PASSWORD"] = password
    from Controll.colab_client import connection_settings
    connection_settings()
    os.environ["REALFACE_BACKEND"] = "colab"
    runpy.run_path(str(Path(__file__).resolve().parent / "app.py"), run_name="__main__")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n起動を中止しました。")
