"""Colab側の画像生成API。画面はPC側、FADINGだけここで実行。"""
import re
from contextlib import closing
import gradio as gr
from Controll.exe_fading import execute_fading_stream


def generate(image_path, current_age, target_age, gender, request_id):
    if not re.fullmatch(r"[0-9a-f]{32}", request_id):
        raise gr.Error("依頼IDの形式が不正です。")
    try:
        # API利用でも入力チェックはController側で再実行する。
        with closing(execute_fading_stream(image_path, current_age, target_age, gender)) as events:
            for event in events:
                file_path = event["path"] if event["kind"] == "result" else None
                # サーバーの絶対パスは、PC向けの進捗データには含めない。
                public_event = {k: v for k, v in event.items() if k not in ("path", "original_path")}
                yield {"request_id": request_id, "event": public_event}, file_path
    except Exception as error:
        yield {"request_id": request_id,
               "event": {"kind": "error", "text": str(error)}}, None


def build_server():
    with gr.Blocks(title="RealFace 生成受付") as server:
        gr.Markdown("# RealFace 生成受付\n操作はPC側のRealFace画面で行ってください。")
        # これらはAPIの入出力定義。ユーザー向け画面はPC上にある。
        photo = gr.File(type="filepath", visible=False)
        current = gr.Number(visible=False)
        target = gr.Number(visible=False)
        gender = gr.Textbox(visible=False)
        request_id = gr.Textbox(visible=False)
        metadata = gr.JSON(visible=False)
        result = gr.File(visible=False)
        trigger = gr.Button(visible=False)
        trigger.click(generate, [photo, current, target, gender, request_id],
                      [metadata, result], api_name="generate",
                      concurrency_limit=1, concurrency_id="fading")
    return server.queue(max_size=8)
