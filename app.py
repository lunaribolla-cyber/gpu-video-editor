import os
import requests
import uvicorn
import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()
CURRENT_BACKEND_URL = "OFFLINE"

def send_to_colab(zip_file):
    if zip_file is None: 
        return "❌ Error: Please upload a valid .zip file containing your asset folders.", None
    if CURRENT_BACKEND_URL == "OFFLINE":
        return "❌ Error: The GPU backend server is currently offline. Please ask the administrator to start the server.", None
    try:
        files = {'file': (os.path.basename(zip_file.name), open(zip_file.name, 'rb'), 'application/zip')}
        response = requests.post(f"{CURRENT_BACKEND_URL}/process", files=files, timeout=7200)
        if response.status_code == 200:
            output_path = "./final_output_video.mp4"
            with open(output_path, 'wb') as f: f.write(response.content)
            return "🎉 Video Generation Success! Use the download box below to save it.", output_path
        return f"❌ Backend Error: {response.text}", None
    except Exception as e:
        return f"❌ Connection Error: {str(e)}", None

with gr.Blocks(title="Pro GPU Video Studio") as demo:
    gr.Markdown("# 🚀 Pro GPU Video Studio")
    gr.Markdown("Upload a single **ZIP file** containing your 3 asset folders (`images`, `voiceover`, and `subtitle`).")
    zip_input = gr.File(label="Upload Assets ZIP File", file_types=[".zip"])
    submit_btn = gr.Button("Generate Video", variant="primary")
    output_log = gr.Textbox(label="Status Log", interactive=False)
    file_output = gr.File(label="📥 Download Your Final Video")
    submit_btn.click(fn=send_to_colab, inputs=zip_input, outputs=[output_log, file_output])

@app.post("/update_backend")
async def update_backend(request: Request):
    global CURRENT_BACKEND_URL
    data = await request.json()
    CURRENT_BACKEND_URL = data.get("url", "OFFLINE")
    return JSONResponse(content={"status": "updated"})

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
