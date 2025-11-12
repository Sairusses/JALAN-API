from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from pdf2image import convert_from_path
import os
import shutil
import subprocess
import sys
import json
from pathlib import Path

app = FastAPI(title="OMRChecker FastAPI")

# Base directories
HF_HOME = "/tmp/huggingface"
INPUT_DIR = f"{HF_HOME}/inputs"
OUTPUT_DIR = f"{HF_HOME}/outputs"

# Ensure directories exist
os.environ["HF_HOME"] = HF_HOME
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.post("/process-omr")
async def process_omr(
    config: UploadFile = File(...),
    evaluation: UploadFile = File(...),
    template: UploadFile = File(...),
    omr_marker: UploadFile = File(...),
    pdf_file: UploadFile = File(...),
):
    """
    Receives OMR-related files, processes them, and returns the analysis results.
    """

    # Clear old input/output data
    shutil.rmtree(INPUT_DIR, ignore_errors=True)
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save all uploaded files to INPUT_DIR
    uploaded_files = {
        "config.json": config,
        "evaluation.json": evaluation,
        "template.json": template,
        "omr_marker.jpg": omr_marker,
        pdf_file.filename: pdf_file,
    }

    for filename, file in uploaded_files.items():
        file_path = os.path.join(INPUT_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    # Convert PDF to image(s)
    pdf_path = os.path.join(INPUT_DIR, pdf_file.filename)
    images = convert_from_path(pdf_path)
    image_paths = []

    for i, img in enumerate(images):
        img_filename = f"converted_page_{i+1}.jpg"
        img_output_path = os.path.join(INPUT_DIR, img_filename)
        img.save(img_output_path, "JPEG")
        image_paths.append(img_output_path)

    # Run main.py as subprocess
    script_path = os.path.join(os.path.dirname(__file__), "main.py")

    subprocess.call([
        sys.executable,
        script_path,
        "--inputDir", INPUT_DIR,
        "--outputDir", OUTPUT_DIR,
    ])

    # Expected output files
    response_json = os.path.join(OUTPUT_DIR, "read_response.json")
    score_txt = os.path.join(OUTPUT_DIR, "score.txt")

    # Collect outputs for response
    results = {
        "converted_images": [],
        "read_response": None,
        "score": None
    }

    # Add converted image outputs (from input dir or output dir depending on your flow)
    output_images = [
        os.path.join(OUTPUT_DIR, f)
        for f in os.listdir(OUTPUT_DIR)
        if f.endswith(".jpg")
    ]

    for img_path in output_images:
        results["converted_images"].append(img_path)

    # Read read_response.json
    if os.path.exists(response_json):
        with open(response_json, "r") as f:
            results["read_response"] = json.load(f)

    # Read score.txt
    if os.path.exists(score_txt):
        with open(score_txt, "r") as f:
            results["score"] = f.read().strip()

    return JSONResponse(content=results)
