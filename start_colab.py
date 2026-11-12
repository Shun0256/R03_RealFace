"""Colabで生成する場合の起動入口。画面は既存のapp.pyを使う。"""
import os
import runpy
from getpass import getpass
from pathlib import Path


def main():
    print("先にcolab/RealFace_Colab_Server.ipynbで受付サーバーを起動してください。")
    os.environ["REALFACE_COLAB_URL"] = input("Colabの公開URL：https://...gradio.live → ").strip()
    os.environ["REALFACE_COLAB_USER"] = "realface"
    os.environ["REALFACE_COLAB_PASSWORD"] = getpass("Colabで設定したパスワード：")
    from Controll.colab_client import connection_settings
    connection_settings()
    os.environ["REALFACE_BACKEND"] = "colab"
    # 既存app.pyの画面構成と起動設定をそのまま使う。
    runpy.run_path(str(Path(__file__).resolve().parent / "app.py"), run_name="__main__")


if __name__ == "__main__":
    main()
