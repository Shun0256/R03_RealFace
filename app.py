"""R03_RealFace直下に配置し、python app.py で起動する。"""
import inspect
import math
import re
import time
from collections import deque
from contextlib import closing
from html import escape

import gradio as gr

from Controll.exe_fading import execute_fading_stream
from View.input_data import CSS, create_input
from View.result import create_result


def convert_input(current_age, years_after, gender):
    """画面の経過年数と性別を、FADING用の値に変換する。"""
    try:
        age, years = float(current_age), float(years_after)
    except (ValueError, TypeError, OverflowError) as error:
        raise ValueError("年齢と経過年数を入力してください。") from error
    if not math.isfinite(age) or not age.is_integer() or not 10 <= age <= 70:
        raise ValueError("現在の年齢は10〜70歳の整数で入力してください。")
    if (not math.isfinite(years) or not years.is_integer()
            or years <= 0 or years % 5 != 0):
        raise ValueError("経過年数は5年以上、5年刻みで選択してください。")
    age, years = int(age), int(years)
    if age + years > 70:
        raise ValueError("変換後の年齢が70歳以下になるように選択してください。")
    gender_value = {"男性": "male", "女性": "female"}.get(gender)
    if gender_value is None:
        raise ValueError("性別を選択してください。")
    return age, years, gender_value


def parse_log(line, stage, counter):
    """既知の段階名とtqdmの回数を抽出。全体の%とは扱わない。"""
    lower = line.lower()
    markers = (
        ("loading pipeline components", "モデルを読み込んでいます"),
        ("loading checkpoint shards", "モデルを読み込んでいます"),
        ("ddim inversion", "画像の解析（DDIM inversion）"),
        ("null-text optimization", "画像の最適化（Null-text optimization）"),
    )
    for marker, label in markers:
        if marker in lower:
            stage, counter = label, None
            break
    # 例: 24%|...| 120/500 [01:30<...]
    match = re.search(r"\d+(?:\.\d+)?%\|.*?\|\s*(\d+)\s*/\s*(\d+)", line)
    if match:
        done, total = map(int, match.groups())
        if total > 0 and 0 <= done <= total:
            # 100%後や別の総数になったら次のループとして扱う。
            if counter and (total != counter[1] or done < counter[0]):
                stage = "FADINGの次の処理"
            counter = (done, total)
    elif line and not any(marker in lower for marker, _ in markers):
        # 別のログが挟まった後まで、直前の100%表示を残さない。
        if counter and counter[0] == counter[1]:
            stage, counter = "FADINGの処理を続けています", None
    return stage, counter


def progress_html(stage, counter, elapsed, error=False):
    seconds = int(elapsed)
    duration = f"{seconds // 60}分{seconds % 60:02d}秒"
    if error:
        bar = ""
        detail = "処理を終了しました。下のボタンから入力画面に戻れます。"
    elif counter is None:
        bar = '<progress aria-label="処理中" style="width:100%;height:22px"></progress>'
        detail = "進捗数値の通知を待っています。"
    else:
        done, total = counter
        percent = 100 * done / total
        bar = (f'<progress value="{done}" max="{total}" aria-label="現在の処理の進捗" '
               'style="width:100%;height:22px"></progress>')
        detail = f"現在の処理：{done} / {total}（{percent:.0f}%）"
    return (
        '<div style="padding:24px;border:1px solid #94a3b8;border-radius:12px">'
        f'<h2>{escape(stage)}</h2><p>{detail}</p>{bar}'
        f'<p>経過時間：{duration}</p></div>'
    )


def build_app():
    options = {"title": "RealFace ～数年後の君へ～"}
    if "css" in inspect.signature(gr.Blocks.__init__).parameters:
        options["css"] = CSS
    with gr.Blocks(**options) as app:
        with gr.Column(visible=True) as input_page:
            image_path, age, years, gender, generate_button = create_input()
        with gr.Column(visible=False) as running_page:
            gr.Markdown("# 顔画像を生成しています")
            status = gr.HTML()
            gr.Markdown(
                "進捗は**現在の処理段階**のものです。100%になっても次の処理が続く場合があります。\n\n"
                "ログが更新されない時間もあります。経過時間の更新だけでは、計算が進んでいるかは判断できません。"
            )
            with gr.Accordion("詳しい実行ログ", open=False):
                log_box = gr.Textbox(label="最新のログ", lines=12, interactive=False)
            error_back = gr.Button("入力画面に戻る", visible=False)
        with gr.Column(visible=False) as result_page:
            (result_image, original_image, age_text, compare_button,
             download_button, retry_button) = create_result()

        def generate_face(image_value, age_value, years_value, gender_value):
            started = time.monotonic()
            stage, counter = "生成の準備をしています", None
            logs = deque(maxlen=30)
            yield {
                input_page: gr.Column(visible=False),
                running_page: gr.Column(visible=True),
                result_page: gr.Column(visible=False),
                generate_button: gr.Button(interactive=False),
                error_back: gr.Button(visible=False),
                status: progress_html(stage, counter, 0), log_box: "",
                result_image: None, original_image: gr.Image(value=None, visible=False),
                download_button: gr.DownloadButton(value=None),
            }
            try:
                current, after, sex = convert_input(age_value, years_value, gender_value)
                last_update = 0
                # closingにより、途中でジェネレーターが閉じられたときも後処理を行う。
                with closing(execute_fading_stream(image_value, current, current + after, sex)) as events:
                    for event in events:
                        kind = event["kind"]
                        if kind == "result":
                            yield {
                                running_page: gr.Column(visible=False),
                                result_page: gr.Column(visible=True),
                                generate_button: gr.Button(interactive=True),
                                result_image: event["path"],
                                original_image: gr.Image(value=event["original_path"], visible=False),
                                age_text: f"### {after}年後の顔（{current}歳 → {current + after}歳）",
                                download_button: event["path"],
                            }
                            return
                        if kind == "stage":
                            stage, counter = event["text"], None
                        elif kind == "log":
                            logs.append(event["text"])
                            stage, counter = parse_log(event["text"], stage, counter)
                        now = time.monotonic()
                        # 高頻度のログでブラウザが重くならないよう更新を間引く。
                        if kind == "stage" or now - last_update >= 0.5:
                            yield {
                                status: progress_html(stage, counter, now - started),
                                log_box: "\n".join(logs),
                            }
                            last_update = now
            except Exception as error:
                # 失敗しても実行中のまま固まらず、入力画面へ戻れるようにする。
                logs.append(str(error))
                yield {
                    status: progress_html(f"生成できませんでした：{error}", None,
                                          time.monotonic() - started, error=True),
                    log_box: "\n".join(logs),
                    error_back: gr.Button(visible=True),
                    generate_button: gr.Button(interactive=True),
                }

        generate_button.click(
            fn=generate_face, inputs=[image_path, age, years, gender],
            outputs=[input_page, running_page, result_page, generate_button,
                     error_back, status, log_box, result_image, original_image,
                     age_text, download_button],
            concurrency_limit=1, concurrency_id="fading", show_progress="hidden",
        )
        compare_button.click(
            fn=lambda: gr.Image(visible=True), inputs=[], outputs=original_image, queue=False,
        )

        def return_to_input():
            return (gr.Column(visible=True), gr.Column(visible=False), gr.Column(visible=False))

        for button in (retry_button, error_back):
            button.click(fn=return_to_input, inputs=[],
                         outputs=[input_page, running_page, result_page], queue=False)
    return app


if __name__ == "__main__":
    app = build_app()
    launch_options = {"inbrowser": True}
    if "css" not in inspect.signature(gr.Blocks.__init__).parameters:
        launch_options["css"] = CSS
    app.queue().launch(**launch_options)
