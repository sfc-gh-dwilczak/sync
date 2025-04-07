import os
import boto3
import tempfile
import snowflake.connector
from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from moviepy.editor import VideoFileClip
import moviepy.video.fx.all as vfx

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# S3 configuration
S3_BUCKET = "danielwilczak"  # <-- update with your S3 bucket name
s3_client = boto3.client('s3')

# Function to write metadata to Snowflake
def write_metadata_to_snowflake(metadata: "VideoMetadata"):
    conn = snowflake.connector.connect(
        user='danielwilczak',
        password='...',
        account='easyconnect-demo',
        warehouse='development',
        database='sync',
        schema='container'
    )
    cur = conn.cursor()
    try:
        width, height = metadata.resolution if len(metadata.resolution) >= 2 else (None, None)
        insert_sql = """
            INSERT INTO VIDEO_METADATA (filename, duration, fps, width, height)
            VALUES (%s, %s, %s, %s, %s)
        """
        cur.execute(insert_sql, (metadata.filename, metadata.duration, metadata.fps, width, height))
        conn.commit()
    finally:
        cur.close()
        conn.close()

@app.on_event("startup")
async def startup_event():
    print("Starting up and listing S3 bucket contents...")
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET)
        if "Contents" in response:
            for obj in response["Contents"]:
                print(obj["Key"])
        else:
            print("Bucket is empty or does not exist")
    except Exception as e:
        print(f"Error listing S3 bucket: {e}")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET)
        if "Contents" in response:
            video_files = [obj["Key"] for obj in response["Contents"] if obj["Key"].endswith(".mp4")]
        else:
            video_files = []
    except Exception as e:
        video_files = []
        print(f"Error listing files from S3: {e}")
    return templates.TemplateResponse("index.html", {"request": request, "files": video_files})

class VideoMetadata(BaseModel):
    filename: str
    duration: float
    fps: float
    resolution: list

@app.post("/process-video")
async def process_video_udf(request: Request):
    """
    Expects a JSON payload with this format:
      {
        "data": [
          [row_index, filename],
          ...
        ]
      }
    Returns:
      {
        "data": [
          [row_index, result_string],
          ...
        ]
      }
    """
    try:
        message = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON payload"})

    if not message or "data" not in message or not message["data"]:
        return {"data": []}

    input_rows = message["data"]
    output_rows = []

    for row in input_rows:
        try:
            row_index = row[0]
            filename = row[1]
        except Exception:
            output_rows.append([row[0] if row and len(row) > 0 else None, f"Invalid row format: {row}"])
            continue

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
                local_input_path = tmp_in.name
            s3_client.download_file(S3_BUCKET, filename, local_input_path)
        except Exception as e:
            output_rows.append([row_index, f"Error downloading video from S3: {e}"])
            continue

        try:
            clip = VideoFileClip(local_input_path)
        except Exception as e:
            output_rows.append([row_index, f"Error loading video: {e}"])
            continue

        metadata = VideoMetadata(
            filename=filename,
            duration=clip.duration,
            fps=clip.fps,
            resolution=clip.size
        )

        clip_bw = clip.fx(vfx.blackwhite)

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_out:
                local_output_path = tmp_out.name
            clip_bw.write_videofile(local_output_path, audio=True, verbose=False, logger=None)
        except Exception as e:
            output_rows.append([row_index, f"Error processing video: {e}"])
            continue
        finally:
            clip.close()
            clip_bw.close()

        bw_filename = f"bw_{filename}"
        try:
            s3_client.upload_file(local_output_path, S3_BUCKET, bw_filename)
        except Exception as e:
            output_rows.append([row_index, f"Error uploading processed video to S3: {e}"])
            continue

        try:
            os.remove(local_input_path)
            os.remove(local_output_path)
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}")

        try:
            write_metadata_to_snowflake(metadata)
        except Exception as e:
            print(f"Error writing metadata to Snowflake: {e}")

        result_str = (
            f"Processed: {metadata.filename}, "
            f"duration: {metadata.duration:.2f}s, "
            f"fps: {metadata.fps:.2f}, "
            f"resolution: {metadata.resolution}"
        )
        output_rows.append([row_index, result_str])

    return {"data": output_rows}