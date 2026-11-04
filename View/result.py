import gradio as gr


with gr.Blocks(title="20年後の顔") as app:

    # 結果画像を表示する場所
    result_image = gr.Image(
        label="結果画像",
        type="pil",
        width=320,
        height=320
    )

    # 比較ボタン
    compare_button = gr.Button(
        "比較",
        size="lg"
    )

    # 年齢表示
    age_text = gr.Markdown(
        "### 20年後の顔"
    )

    # 下のボタン
    with gr.Row():

        download_button = gr.DownloadButton(
            "ダウンロード"
        )

        retry_button = gr.Button(
            "もう一回やる！"
        )


app.launch()
