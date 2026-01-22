import os
import time
import uuid
import json
import asyncio
import aiofiles
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import lyria_generator
import audio_utils
import gemini_vibe_agent
import video_processor

app = FastAPI(title="Lyria Audio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)


class GenerateRequest(BaseModel):
    prompt: str


@app.get("/")
def health_check():
    return {"status": "Lyria Backend is running 🚀"}


@app.post("/generate")
async def generate_audio(req: GenerateRequest):
    try:
        filename = f"track_{int(time.time())}_{uuid.uuid4().hex[:4]}.wav"
        
        print(f"--> Generating: {req.prompt}")
        
        # Use Gemini to intelligently analyze if a negative prompt would help
        negative_prompt = await gemini_vibe_agent.analyze_prompt_for_negative(req.prompt)
        if negative_prompt:
            print(f"--> Applying intelligent negative prompt: {negative_prompt}")

        result_path = await lyria_generator.generate_music_file(
            prompt=req.prompt,
            negative_prompt=negative_prompt,
            seed=None,  # Always use None to allow multiple samples if needed
            output_filename=filename
        )

        if not result_path:
            raise HTTPException(status_code=500, detail="Error in Lyria Generator")

        response = FileResponse(path=result_path, media_type="audio/wav", filename=filename)
        return response

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/check-ffmpeg")
def check_ffmpeg():
    """Health check endpoint to verify FFmpeg installation."""
    is_installed = video_processor.check_ffmpeg_installed()
    version = video_processor.get_ffmpeg_version()
    
    return {
        "ffmpeg_installed": is_installed,
        "ffmpeg_version": version,
        "status": "ready" if is_installed else "ffmpeg_not_found"
    }


@app.post("/video-to-music-stream")
async def video_to_music_stream(video: UploadFile = File(...)):
    """
    Streaming version of video-to-music that sends real-time status updates.
    Returns Server-Sent Events (SSE) with progress updates.
    """
    
    async def generate_status_stream():
        # Generate unique filenames
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex[:6]
        original_ext = Path(video.filename).suffix if video.filename else '.mp4'
        
        temp_video_path = f"temp_video_{timestamp}_{unique_id}{original_ext}"
        temp_audio_path = f"temp_audio_{timestamp}_{unique_id}.wav"
        output_video_path = f"video_with_music_{timestamp}_{unique_id}.mp4"
        
        try:
            # Validate FFmpeg
            if not video_processor.check_ffmpeg_installed():
                yield f"data: {json.dumps({'status': 'error', 'message': 'FFmpeg not installed'})}\n\n"
                return
            
            # Validate file type
            if not video.content_type or not video.content_type.startswith('video/'):
                yield f"data: {json.dumps({'status': 'error', 'message': 'Invalid file type'})}\n\n"
                return
            
            # Step 1: Save video
            yield f"data: {json.dumps({'status': 'uploading', 'stage': 1, 'message': 'Saving uploaded video...'})}\n\n"
            async with aiofiles.open(temp_video_path, 'wb') as f:
                content = await video.read()
                await f.write(content)
            
            if not video_processor.validate_video_file(temp_video_path):
                yield f"data: {json.dumps({'status': 'error', 'message': 'Unsupported video format'})}\n\n"
                return
            
            # Step 2: Analyze with Gemini
            yield f"data: {json.dumps({'status': 'analyzing', 'stage': 2, 'message': 'Analyzing video with Gemini AI...'})}\n\n"
            
            try:
                # We'll need to modify gemini_vibe_agent to support callbacks
                music_prompt = await gemini_vibe_agent.analyze_video_for_music(temp_video_path)
                yield f"data: {json.dumps({'status': 'analyzed', 'stage': 2, 'message': f'Generated prompt: {music_prompt[:50]}...'})}\n\n"
            except Exception as gemini_error:
                music_prompt = "Energetic instrumental composition at 128 BPM featuring layered analog synthesizers, punchy electronic drums with side-chain compression, arpeggiated bassline in D minor, bright pad textures, and rhythmic hi-hat patterns creating an uplifting modern electronic atmosphere"
                yield f"data: {json.dumps({'status': 'fallback', 'stage': 2, 'message': 'Using fallback prompt'})}\n\n"
            
            # Step 3: Generate music
            yield f"data: {json.dumps({'status': 'generating', 'stage': 3, 'message': 'Generating music with Lyria 2...'})}\n\n"
            
            audio_result = await lyria_generator.generate_music_file(
                prompt=music_prompt,
                negative_prompt="",
                seed=None,
                output_filename=temp_audio_path
            )
            
            if not audio_result:
                yield f"data: {json.dumps({'status': 'error', 'message': 'Failed to generate music'})}\n\n"
                return
            
            yield f"data: {json.dumps({'status': 'generated', 'stage': 3, 'message': 'Music generated successfully'})}\n\n"
            
            # Step 4: Merge
            yield f"data: {json.dumps({'status': 'merging', 'stage': 4, 'message': 'Merging audio with video...'})}\n\n"
            
            final_video = await video_processor.merge_audio_with_video(
                video_path=temp_video_path,
                audio_path=temp_audio_path,
                output_path=output_video_path,
                overwrite=True
            )
            
            # Clean up
            try:
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
            except:
                pass
            
            # Success
            yield f"data: {json.dumps({'status': 'complete', 'stage': 4, 'message': 'Video ready!', 'filename': f'video_with_music_{unique_id}.mp4', 'musicPrompt': music_prompt})}\n\n"
            
        except Exception as e:
            # Clean up on error
            for temp_file in [temp_video_path, temp_audio_path, output_video_path]:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
            
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_status_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/video-to-music")
async def video_to_music(
    video: UploadFile = File(...),
    output_type: str = "merged"  # "merged" or "audio_only"
):
    """
    Complete video-to-music workflow:
    1. Upload video file
    2. Analyze with Gemini to generate music prompt
    3. Generate music with Lyria 2
    4. Either merge audio with video (default) or return audio only
    5. Return final result based on output_type
    
    Args:
        video: Uploaded video file
        output_type: "merged" (default) returns video with music, "audio_only" returns just the audio
    """
    
    # Validate output_type parameter
    if output_type not in ["merged", "audio_only"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid output_type. Must be 'merged' or 'audio_only', got: {output_type}"
        )
    
    # Validate FFmpeg is installed (only needed for merged output)
    if output_type == "merged" and not video_processor.check_ffmpeg_installed():
        raise HTTPException(
            status_code=500,
            detail="FFmpeg is not installed. Please install FFmpeg to use video merging features."
        )
    
    # Validate file type
    if not video.content_type or not video.content_type.startswith('video/'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Expected video file, got: {video.content_type}"
        )
    
    # Generate unique filenames
    timestamp = int(time.time())
    unique_id = uuid.uuid4().hex[:6]
    
    # Determine file extension from original filename
    original_ext = Path(video.filename).suffix if video.filename else '.mp4'
    
    temp_video_path = f"temp_video_{timestamp}_{unique_id}{original_ext}"
    temp_audio_path = f"temp_audio_{timestamp}_{unique_id}.wav"
    output_video_path = f"video_with_music_{timestamp}_{unique_id}.mp4"
    
    try:
        # Step 1: Save uploaded video
        print(f"[1/{'4' if output_type == 'merged' else '3'}] Saving uploaded video: {video.filename}")
        async with aiofiles.open(temp_video_path, 'wb') as f:
            content = await video.read()
            await f.write(content)
        
        # Validate the saved video file
        if not video_processor.validate_video_file(temp_video_path):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported video format. Supported formats: {', '.join(video_processor.SUPPORTED_VIDEO_FORMATS)}"
            )
        
        # Step 2: Analyze video with Gemini to get music prompt
        print(f"[2/{'4' if output_type == 'merged' else '3'}] Analyzing video with Gemini 1.5 Pro...")
        try:
            music_prompt = await gemini_vibe_agent.analyze_video_for_music(temp_video_path)
            print(f"Generated music prompt: {music_prompt}")
        except Exception as gemini_error:
            print(f"Gemini analysis failed: {gemini_error}")
            # Use safe fallback prompt to avoid recitation filter
            music_prompt = "Energetic instrumental composition at 128 BPM featuring layered analog synthesizers, punchy electronic drums with side-chain compression, arpeggiated bassline in D minor, bright pad textures, and rhythmic hi-hat patterns creating an uplifting modern electronic atmosphere"
            print(f"Using safe fallback prompt: {music_prompt}")
        
        # Step 3: Generate music with Lyria 2
        print(f"[3/{'4' if output_type == 'merged' else '3'}] Generating music with Lyria 2...")
        audio_result = await lyria_generator.generate_music_file(
            prompt=music_prompt,
            negative_prompt="",
            seed=None,
            output_filename=temp_audio_path
        )
        
        if not audio_result:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate music with Lyria"
            )
        
        # Handle output based on user preference
        if output_type == "audio_only":
            # Return just the audio file
            print(f"✓ Music generation complete: {temp_audio_path}")
            
            # Clean up video file
            try:
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
            except Exception as cleanup_error:
                print(f"Cleanup warning: {cleanup_error}")
            
            return FileResponse(
                path=temp_audio_path,
                media_type="audio/wav",
                filename=f"music_{unique_id}.wav",
                headers={
                    "X-Music-Prompt": music_prompt
                }
            )
        else:
            # Step 4: Merge audio with video using FFmpeg
            print(f"[4/4] Merging audio with video...")
            final_video = await video_processor.merge_audio_with_video(
                video_path=temp_video_path,
                audio_path=temp_audio_path,
                output_path=output_video_path,
                overwrite=True
            )
            
            # Clean up temporary files
            try:
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
            except Exception as cleanup_error:
                print(f"Cleanup warning: {cleanup_error}")
            
            # Return the final video
            print(f"✓ Video-to-music complete: {final_video}")
            
            return FileResponse(
                path=final_video,
                media_type="video/mp4",
                filename=f"video_with_music_{unique_id}.mp4",
                headers={
                    "X-Music-Prompt": music_prompt
                }
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Clean up on error
        for temp_file in [temp_video_path, temp_audio_path, output_video_path]:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        
        print(f"Error in video-to-music workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Video processing failed: {str(e)}")