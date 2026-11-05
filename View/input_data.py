import gradio as gr

# CSSで全体をスケールアップ ＋ ボタンを青色に変更
CSS = """
/* 画面幅の制限を広げて中央寄せ */
#main-col {
    max-width: 1400px;
    margin: 0 auto;
    padding: 30px;
}

/* タイトル・説明文の拡大 */
#header-title { font-size: 2.2rem !important; font-weight: bold; }
#header-desc { font-size: 1.2rem !important; margin-bottom: 20px; }

/* 右側（設定エリア）の縦位置・余白の拡大 */
#right-col {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 32px;
    padding: 0 24px;
}

/* 各ラベル（項目名）の文字を大きく */
#right-col label span { 
    font-size: 1.5rem !important; 
    font-weight: bold;
    margin-bottom: 8px;
}

/* 入力ボックス（数値・ドロップダウン）の文字と高さを拡大 */
#right-col input, #right-col .single-select { 
    font-size: 1.6rem !important; 
    height: 64px !important; 
}

/* 生成ボタンを特大＆青色に変更 */
#gen-btn {
    font-size: 2.0rem !important;
    font-weight: bold;
    min-height: 90px !important;
    margin-top: 16px;
    background-color: #1d4ed8 !important; /* 青色 (ロイヤルブルー) */
    color: #ffffff !important;           /* 文字色は白 */
    border: none !important;
}

/* マウスを乗せた（ホバー）時の色（少し濃い青） */
#gen-btn:hover {
    background-color: #1e40af !important;
}
"""


def update_target_age_range(current_age):
    if current_age is None:
        return gr.Dropdown(choices=[0], value=0)
    try:
        current_age = int(current_age)
    except ValueError:
        return gr.Dropdown(choices=[0], value=0)

    current_age = max(10, min(70, current_age))
    max_step = ((70 - current_age) // 5) * 5
    max_step = max(max_step, 0)
    choices = list(range(0, max_step + 1, 5))

    return gr.Dropdown(choices=choices, value=choices[-1] if choices else 0)

def create_input():
    """入力画面を作り、app.pyで使用する部品を返す。"""
    with gr.Column(elem_id="main-col"):
        # ヘッダー
        gr.Markdown("# Real Face", elem_id="header-title")
        gr.Markdown(
            "顔写真をアップロードし、年齢・性別と経過年数を設定してください。",
            elem_id="header-desc",
        )

        with gr.Row():
            # 左カラム：画像ドロップエリア
            with gr.Column(scale=1):
                imagepath = gr.Image(
                    label="顔写真を選ぶ",
                    type="filepath",
                    sources=["upload"],
                    height=650,
                )

            # 右カラム：設定パネル
            with gr.Column(scale=1, elem_id="right-col"):
                with gr.Group():
                    current_age = gr.Number(
                        value=20,
                        label="年齢 (10〜70)",
                        minimum=10,
                        maximum=70,
                        precision=0,
                    )
                    gender = gr.Dropdown(
                        choices=["男性", "女性"],
                        value="男性",
                        label="性別",
                    )
                    target_age = gr.Dropdown(
                        choices=[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
                        value=50,
                        label="何年後の顔を見る(5歳刻み)",
                    )

                execute_btn = gr.Button(
                    "生成！", variant="primary", elem_id="gen-btn"
                )

    # イベントハンドラ
    current_age.change(
        fn=update_target_age_range,
        inputs=current_age,
        outputs=target_age,
    )

    return imagepath, current_age, target_age, gender, execute_btn
