import gradio as gr


def create_result():
    """結果画面の部品を作る。起動や生成処理はapp.pyが担当する。"""
    age_text = gr.Markdown("### 生成結果")
    with gr.Row():
        original_image = gr.Image(
            label="変換前", type="filepath", width=320, height=320,
            interactive=False, visible=False,
        )
        result_image = gr.Image(
            label="結果画像", type="filepath", width=320, height=320,
            interactive=False,
        )
    compare_button = gr.Button("比較", size="lg")
    with gr.Row():
        download_button = gr.DownloadButton("ダウンロード")
        retry_button = gr.Button("もう一回やる！")
    return (result_image, original_image, age_text, compare_button,
            download_button, retry_button)
