from pathlib import Path
from uuid import uuid4
import math
import subprocess
import os
import re
from queue import Queue, Empty
from threading import Thread

from PIL import Image, ImageOps


# ===== フォルダ・ファイルの場所 =====

# R03_RealFace
PROJECT_DIR = Path(__file__).resolve().parent.parent

# R4S115（R03_RealFaceの1つ上）
ROOT_DIR = PROJECT_DIR.parent

# FADING本体
FADING_DIR = ROOT_DIR / "FADING_stable"

# FADING用の仮想環境のPython
PYTHON_PATH = ROOT_DIR / ".venv_fading" / "Scripts" / "python.exe"

# 学習済みモデル
MODEL_DIR = ROOT_DIR / "model" / "finetune_double_prompt_150_random"

# 入力画像・生成画像の保存先
WORK_DIR = PROJECT_DIR / "fading_results"


# ===== 入力内容の確認 =====

def check_input(image_path, current_age, target_age):
    """画像と年齢を確認し、処理に使える形式で返す。"""

    if image_path is None or str(image_path).strip() == "":
        raise ValueError("顔写真を選択してください。")

    image_path = Path(image_path).resolve()

    if not image_path.is_file():
        raise ValueError("選択した画像ファイルが見つかりません。")

    # 画像として読み込めるか確認
    try:
        with Image.open(image_path) as image:
            image.verify()
    except (OSError, ValueError, SyntaxError) as error:
        raise ValueError(
            "画像を読み込めません。別の画像を選択してください。"
        ) from error

    ages = []

    for label, value in [
        ("現在の年齢", current_age),
        ("変換後の年齢", target_age),
    ]:
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(
                f"{label}を数値で入力してください。"
            ) from error

        if not math.isfinite(number) or not number.is_integer():
            raise ValueError(f"{label}は整数で入力してください。")

        # このアプリでは0～100歳に制限
        if not 0 <= number <= 100:
            raise ValueError(
                f"{label}は0～100歳で入力してください。"
            )

        ages.append(int(number))

    current_age, target_age = ages

    if current_age == target_age:
        raise ValueError("現在と異なる年齢を指定してください。")

    return image_path, current_age, target_age


# ===== 入力画像の準備 =====

def prepare_image(image_path):
    """画像の向き・色形式を整え、実行専用フォルダに保存する。"""

    # 実行ごとに別のフォルダを作る
    run_dir = WORK_DIR / uuid4().hex
    run_dir.mkdir(parents=True, exist_ok=False)

    # 入力画像の保存先
    prepared_path = run_dir / "input.png"

    # 生成画像の保存先
    output_dir = run_dir / "output"
    output_dir.mkdir()

    with Image.open(image_path) as image:
        # スマホ写真などの向き情報を反映
        image = ImageOps.exif_transpose(image)

        # RGB形式に統一
        image = image.convert("RGB")

        # 元画像を上書きせず、別の画像として保存
        image.save(prepared_path, format="PNG")

    return prepared_path, output_dir


# ===== FADINGの実行 =====

def run_fading_stream(
    image_path,
    current_age,
    target_age,
    output_dir,
    gender,
):
    """FADINGを実行し、処理が終わるまで待つ。"""

    if gender not in ("male", "female"):
        raise ValueError(
            "genderはmaleまたはfemaleを指定してください。"
        )

    script_path = FADING_DIR / "age_editing.py"

    if not PYTHON_PATH.is_file():
        raise FileNotFoundError(
            f"仮想環境のPythonが見つかりません：{PYTHON_PATH}"
        )

    if not script_path.is_file():
        raise FileNotFoundError(
            f"FADINGの実行ファイルが見つかりません：{script_path}"
        )

    if not (MODEL_DIR / "model_index.json").is_file():
        raise FileNotFoundError(
            "学習済みモデルのmodel_index.jsonが見つかりません。"
            f"MODEL_DIRを確認してください：{MODEL_DIR}"
        )

    # FADINGへ渡す実行コマンド
    command = [
        str(PYTHON_PATH),
        "-u",
        str(script_path),
        "--image_path", image_path.as_posix(),
        "--age_init", str(current_age),
        "--gender", gender,
        "--save_aged_dir", output_dir.as_posix(),
        "--specialized_path", MODEL_DIR.as_posix(),
        "--target_ages", str(target_age),
    ]

    # tqdmの進捗はstderrに出るため、stdoutとまとめて読み取る。
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    process = subprocess.Popen(
        command, cwd=str(FADING_DIR), stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        errors="replace", bufsize=1, env=env,
    )
    messages = Queue()

    def read_output():
        try:
            # text=Trueで、tqdmの\rによる更新も行単位で読める。
            for line in process.stdout:
                messages.put(line)
        finally:
            messages.put(None)

    reader = Thread(target=read_output, daemon=True)
    reader.start()
    try:
        while True:
            try:
                line = messages.get(timeout=1)
            except Empty:
                # ログのない計算中も、Web側の経過時間を更新する。
                yield {"kind": "heartbeat"}
                continue
            if line is None:
                break
            line = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", line).strip()
            if line:
                print(line, flush=True)
                yield {"kind": "log", "text": line}
        code = process.wait()
        if code != 0:
            raise RuntimeError(
                f"FADINGの処理に失敗しました（終了コード：{code}）。"
                "実行ログまたはターミナルを確認してください。"
            )
    finally:
        # ジェネレーターが閉じられたときにも子プロセスを残さない。
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        reader.join(timeout=2)
        process.stdout.close()


def run_fading(image_path, current_age, target_age, output_dir, gender):
    """従来と同じ呼び方も維持する。"""
    for _ in run_fading_stream(image_path, current_age, target_age, output_dir, gender):
        pass


# ===== 生成画像の確認 =====

def find_result_image(image_path, target_age, output_dir):
    """生成画像が存在することを確認し、パスを文字列で返す。"""

    # 例：入力がinput.png、変換後が40歳ならinput_40.png
    result_path = output_dir / f"{image_path.stem}_{target_age}.png"

    if not result_path.is_file():
        raise FileNotFoundError(
            "処理は終了しましたが、生成画像が見つかりません："
            f"{result_path}"
        )

    return str(result_path)


# ===== 全体の処理 =====

def execute_fading(
    image_path,
    current_age,
    target_age,
    gender="male",
):
    """入力確認・画像準備・FADING実行・結果取得を順番に行う。"""
    if os.environ.get("REALFACE_BACKEND") == "colab":
        from Controll.colab_client import execute_fading as execute_remote
        return execute_remote(image_path, current_age, target_age, gender)

    image_path, current_age, target_age = check_input(
        image_path,
        current_age,
        target_age,
    )

    prepared_path, output_dir = prepare_image(image_path)

    run_fading(
        prepared_path,
        current_age,
        target_age,
        output_dir,
        gender,
    )

    result_path = find_result_image(
        prepared_path,
        target_age,
        output_dir,
    )

    return result_path


def execute_fading_stream(image_path, current_age, target_age, gender="male"):
    """進捗イベントをyieldし、最後に結果画像のパスを通知する。"""
    if os.environ.get("REALFACE_BACKEND") == "colab":
        from Controll.colab_client import execute_fading_stream as execute_remote_stream
        yield from execute_remote_stream(image_path, current_age, target_age, gender)
        return
    yield {"kind": "stage", "text": "入力内容を確認しています"}
    image_path, current_age, target_age = check_input(
        image_path, current_age, target_age,
    )
    yield {"kind": "stage", "text": "入力画像を準備しています"}
    prepared_path, output_dir = prepare_image(image_path)
    yield {"kind": "stage", "text": "FADINGを起動しています"}
    yield from run_fading_stream(
        prepared_path, current_age, target_age, output_dir, gender,
    )
    yield {"kind": "stage", "text": "生成画像を確認しています"}
    result_path = find_result_image(prepared_path, target_age, output_dir)
    yield {"kind": "result", "path": result_path, "original_path": str(prepared_path)}
