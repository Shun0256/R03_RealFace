"""result.py

「生成！」ボタンを押したあとの結果画面(View)。

app.py 側で入力画面(main-col)と切り替えて使う想定:
    入力画面 : visible=True  / 結果画面 : visible=False   (初期状態)
    生成後   : 入力画面を隠し、結果画面を表示して結果画像をセット
"""

import gradio as gr

# app.py の CSS に連結して使う(既存の #header-title などはそのまま流用)
RESULT_CSS = """
#result-col {
    max-width: 1400px;
    margin: 0 auto;
    padding: 30px;
}

/* 戻るボタン(生成ボタンと同系色) */
#back-btn {
    font-size: 1.6rem !important;
    font-weight: bold;
    min-height: 72px !important;
    margin-top: 16px;
    background-color: #1d4ed8 !important;
    color: #ffffff !important;
    border: none !important;
}
#back-btn:hover {
    background-color: #1e40af !important;
}
"""


def create_result_view():
    """結果画面を作って返す。gr.Blocks() の中で呼び出すこと。

    Returns:
        result_col   : 結果画面全体(visible の切り替え用)
        result_image : 結果画像(execute_fading の戻り値をセットする)
        back_btn     : 入力画面に戻るボタン
    """
    with gr.Column(visible=False, elem_id="result-col") as result_col:
        gr.Markdown("# Real Face", elem_id="header-title")
        gr.Markdown("生成結果です。", elem_id="header-desc")

        result_image = gr.Image(
            label="結果画像",
            type="pil",          # PIL / numpy / ファイルパスのどれを返しても表示できる
            interactive=False,   # 出力専用
            height=650,
        )

        back_btn = gr.Button("戻る", elem_id="back-btn")

    return result_col, result_image, back_btn