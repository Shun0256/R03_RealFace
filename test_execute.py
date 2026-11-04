from pathlib import Path
from Controll.exe_fading import execute_fading


# test_execute.pyがあるフォルダ
PROJECT_DIR = Path(__file__).resolve().parent

# テストに使う写真
IMAGE_PATH = PROJECT_DIR / "raizin.jpg"


if __name__ == "__main__":
    print("FADINGのテストを開始します。", flush=True)

    result_path = execute_fading(
        image_path=str(IMAGE_PATH),
        current_age=28,
        target_age=60,
        gender="male",
    )

    print("画像生成が完了しました。")
    print(f"生成画像の保存先：{result_path}")