"""PC側の窓口。FADINGは実行せず、Colabへ依頼する。"""
import os
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

from gradio_client import Client, handle_file
from PIL import Image
from .exe_fading import check_input, prepare_image


def connection_settings():
    url = os.environ.get("REALFACE_COLAB_URL", "").strip().rstrip("/")
    user = os.environ.get("REALFACE_COLAB_USER", "realface")
    password = os.environ.get("REALFACE_COLAB_PASSWORD", "")
    parsed = urlparse(url)
    # HTTPはローカル結合テストの場合のみ許可。
    if not parsed.hostname or not (parsed.scheme == "https" or
            (parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost"))):
        raise ValueError("Colabが表示したhttps://から始まるURLを指定してください。")
    if parsed.username or parsed.password:
        raise ValueError("URLにはユーザー名・パスワードを含めないでください。")
    if not password:
        raise ValueError("Colabの接続パスワードが未設定です。start_remote.pyから起動してください。")
    return url, (user, password)


def execute_fading_stream(image_path, current_age, target_age, gender="male"):
    image_path, current_age, target_age = check_input(image_path, current_age, target_age)
    if gender not in ("male", "female"):
        raise ValueError("性別を選択してください。")
    url, auth = connection_settings()
    # 画像をPC側にも保存し、比較に使う。Colab内のパスはPCで使えない。
    prepared, output_dir = prepare_image(image_path)
    request_id = output_dir.parent.name
    yield {"kind": "stage", "text": "Colabへ接続しています"}
    client, job = None, None
    try:
        client = Client(url, auth=auth, verbose=False,
                        download_files=str(output_dir / "received"),
                        httpx_kwargs={"timeout": 120.0})
        yield {"kind": "stage", "text": "写真を送信し、Colabの受付を待っています"}
        job = client.submit(handle_file(str(prepared)), current_age, target_age,
                            gender, request_id, api_name="/generate")
        started = time.monotonic()
        seen = 0
        result_path = None
        # ログがなくてもUIへheartbeatを返す。再送はせず二重生成を避ける。
        while True:
            done = job.done()
            outputs = job.outputs()
            for payload, downloaded in outputs[seen:]:
                if not isinstance(payload, dict) or payload.get("request_id") != request_id:
                    raise RuntimeError("Colabから想定外の応答を受信しました。")
                event = payload["event"]
                if event["kind"] == "error":
                    raise RuntimeError(event["text"])
                if event["kind"] == "result":
                    if not downloaded or not Path(downloaded).is_file():
                        raise RuntimeError("生成画像をPCにダウンロードできませんでした。")
                    with Image.open(downloaded) as image:
                        image.verify()
                    result_path = output_dir / f"input_{target_age}.png"
                    shutil.copyfile(downloaded, result_path)
                else:
                    yield event
            seen = len(outputs)
            if done:
                # 通信や認証に起因するバックグラウンド例外を取り出す。
                job.result()
                if result_path is None:
                    raise RuntimeError("Colabから生成画像が返されませんでした。")
                yield {"kind": "result", "path": str(result_path), "original_path": str(prepared)}
                return
            if time.monotonic() - started > 7200:
                raise TimeoutError("Colabへの依頼から2時間経過しました。Colab側の実行状況を確認してください。")
            yield {"kind": "heartbeat"}
            time.sleep(0.5)
    except Exception as error:
        raise RuntimeError(
            "Colabでの生成・通信に失敗しました。接続URL、パスワード、Colabの実行ログを確認してください。\n"
            f"詳細：{error}"
        ) from error
    finally:
        if job is not None and not job.done():
            try:
                job.cancel()
            except Exception:
                pass
        if client is not None:
            client.close()


def execute_fading(image_path, current_age, target_age, gender="male"):
    for event in execute_fading_stream(image_path, current_age, target_age, gender):
        if event["kind"] == "result":
            return event["path"]
    raise RuntimeError("生成結果がありません。")
