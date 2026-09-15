import os
import requests
import uvicorn
import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()
CURRENT_BACKEND_URL = "OFFLINE"

# Internal tracking dictionaries
job_status = {}
job_files = {}

def send_to_colab(zip_file):
    if zip_file is None: 
        return "❌ Error: Please upload a valid .zip file containing your asset folders.", gr.update(visible=False), None
    if CURRENT_BACKEND_URL == "OFFLINE":
        return "❌ Error: The GPU backend server is currently offline.", gr.update(visible=False), None

    try:
        # Trigger the process instantly and exit out to protect the channel from timing out
        files = {'file': (os.path.basename(zip_file.name), open(zip_file.name, 'rb'), 'application/zip')}
        response = requests.post(f"{CURRENT_BACKEND_URL}/process", files=files)
        
        if response.status_code == 202:
            data = response.json()
            task_id = data.get("task_id")
            return f"🚀 Upload successful! Video task registered. Processing on 16GB VRAM GPU...\nTask ID: {task_id}", gr.update(visible=True), task_id
        else:
            return f"❌ Upload Failed: {response.text}", gr.update(visible=False), None
    except Exception as e:
        return f"❌ Connection Error: {str(e)}", gr.update(visible=False), None

def check_status(task_id):
    if not task_id:
        return "System Idle.", None
        
    global job_status, job_files
    status = job_status.get(task_id, "Processing...")
    
    if status == "SUCCESS":
        video_path = job_files.get(task_id)
        if video_path and os.path.exists(video_path):
            return "🎉 Video Generation Complete! Download your master file below.", video_path
        return "❌ Error: Rendered file missing from workspace cache.", None
    elif "FAILED" in status:
        return f"❌ Processing Crash: {status}", None
        
    return f"⏳ Hardware Rendering Active... Please wait. Status: {status}", None

with gr.Blocks(title="Pro GPU Video Studio") as demo:
    gr.Markdown("# 🚀 Pro GPU Video Studio (Timeout Protected)")
    gr.Markdown("Upload your `.zip` archive package. The system processes the files asynchronously on high-speed hardware.")
    
    task_id_state = gr.State()
    
    with gr.Row():
        zip_input = gr.File(label="Upload Assets ZIP File", file_types=[".zip"])
        
    submit_btn = gr.Button("Generate Video", variant="primary")
    output_log = gr.Textbox(label="System Activity Logs", interactive=False)
    
    # Live status checker card block
    with gr.Column(visible=False) as check_panel:
        status_btn = gr.Button("🔄 Refresh Render Status / Fetch Video", variant="secondary")
        file_output = gr.File(label="📥 Download Your Final Video")

    submit_btn.click(
        fn=send_to_colab, 
        inputs=zip_input, 
        outputs=[output_log, check_panel, task_id_state]
    )
    
    status_btn.click(
        fn=check_status,
        inputs=task_id_state,
        outputs=[output_log, file_output]
    )

@app.post("/update_backend")
async def update_backend(request: Request):
    global CURRENT_BACKEND_URL
    data = await request.json()
    CURRENT_BACKEND_URL = data.get("url", "OFFLINE")
    return JSONResponse(content={"status": "updated"})

@app.post("/webhook_callback")
async def webhook_callback(request: Request):
    global job_status, job_files
    form_data = await request.form()
    task_id = form_data.get("task_id")
    status = form_data.get("status")
    
    if status == "SUCCESS":
        uploaded_file = form_data.get("file")
        save_path = f"./final_output_{task_id}.mp4"
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(uploaded_file.file, buffer)
        job_files[task_id] = save_path
        job_status[task_id] = "SUCCESS"
    else:
        job_status[task_id] = f"FAILED: {form_data.get('error', 'Unknown Error')}"
        
    return JSONResponse(content={"status": "acknowledged"})

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import shutil
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
