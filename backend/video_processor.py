import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional

# Supported video formats
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.mov', '.avi', '.mkv']
SUPPORTED_AUDIO_FORMATS = ['.wav', '.mp3', '.aac']


def check_ffmpeg_installed() -> bool:
    """
    Checks if FFmpeg is installed and available in the system PATH.
    
    Returns:
        True if FFmpeg is available, False otherwise
    """
    return shutil.which('ffmpeg') is not None


def get_ffmpeg_version() -> Optional[str]:
    """
    Gets the installed FFmpeg version.
    
    Returns:
        Version string or None if FFmpeg is not installed
    """
    if not check_ffmpeg_installed():
        return None
    
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        # First line contains version info
        return result.stdout.split('\n')[0]
    except Exception:
        return None


def validate_video_file(file_path: str) -> bool:
    """
    Validates that a file exists and has a supported video format.
    
    Args:
        file_path: Path to the video file
        
    Returns:
        True if valid, False otherwise
    """
    if not os.path.exists(file_path):
        return False
    
    file_ext = Path(file_path).suffix.lower()
    return file_ext in SUPPORTED_VIDEO_FORMATS


def validate_audio_file(file_path: str) -> bool:
    """
    Validates that a file exists and has a supported audio format.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        True if valid, False otherwise
    """
    if not os.path.exists(file_path):
        return False
    
    file_ext = Path(file_path).suffix.lower()
    return file_ext in SUPPORTED_AUDIO_FORMATS


async def merge_audio_with_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    overwrite: bool = True
) -> str:
    """
    Merges an audio track with a video file using FFmpeg.
    
    The original video's audio (if any) is replaced with the new audio track.
    If the audio is shorter than the video, it will loop.
    If the audio is longer, it will be trimmed to match the video duration.
    
    Args:
        video_path: Path to the input video file
        audio_path: Path to the audio file to merge
        output_path: Path for the output video file
        overwrite: Whether to overwrite existing output file
        
    Returns:
        Path to the output video file
        
    Raises:
        ValueError: If FFmpeg is not installed or files are invalid
        Exception: If FFmpeg processing fails
    """
    
    # Validate FFmpeg installation
    if not check_ffmpeg_installed():
        raise ValueError(
            "FFmpeg is not installed. Please install FFmpeg:\n"
            "  macOS: brew install ffmpeg\n"
            "  Linux: sudo apt-get install ffmpeg\n"
            "  Windows: Download from https://ffmpeg.org/download.html"
        )
    
    # Validate input files
    if not validate_video_file(video_path):
        raise ValueError(f"Invalid or missing video file: {video_path}")
    
    if not validate_audio_file(audio_path):
        raise ValueError(f"Invalid or missing audio file: {audio_path}")
    
    print(f"Merging audio with video using FFmpeg...")
    print(f"  Video: {video_path}")
    print(f"  Audio: {audio_path}")
    print(f"  Output: {output_path}")
    
    try:
        # Build FFmpeg command
        # -i: input files
        # -map 0:v: take video stream from first input (video file)
        # -map 1:a: take audio stream from second input (audio file)
        # -c:v copy: copy video codec (no re-encoding for speed)
        # -c:a aac: encode audio as AAC for compatibility
        # -shortest: finish encoding when shortest input ends
        # -y: overwrite output file if it exists
        
        cmd = [
            'ffmpeg',
            '-i', video_path,      # Input video
            '-i', audio_path,       # Input audio
            '-map', '0:v',          # Map video from first input
            '-map', '1:a',          # Map audio from second input
            '-c:v', 'copy',         # Copy video codec (fast)
            '-c:a', 'aac',          # Encode audio as AAC
            '-b:a', '192k',         # Audio bitrate
            '-shortest',            # Match shortest stream duration
        ]
        
        if overwrite:
            cmd.append('-y')
        
        cmd.append(output_path)
        
        # Run FFmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Check for errors
        if result.returncode != 0:
            error_msg = result.stderr
            raise Exception(f"FFmpeg failed: {error_msg}")
        
        # Verify output file was created
        if not os.path.exists(output_path):
            raise Exception("FFmpeg completed but output file was not created")
        
        print(f"Successfully merged audio with video: {output_path}")
        return output_path
        
    except subprocess.TimeoutExpired:
        raise Exception("FFmpeg processing timed out (>5 minutes)")
    except Exception as e:
        print(f"Error during video-audio merge: {e}")
        raise


async def extract_audio_from_video(video_path: str, output_audio_path: str) -> str:
    """
    Extracts audio from a video file using FFmpeg.
    
    Args:
        video_path: Path to the input video file
        output_audio_path: Path for the extracted audio file
        
    Returns:
        Path to the extracted audio file
        
    Raises:
        ValueError: If FFmpeg is not installed or video is invalid
        Exception: If FFmpeg processing fails
    """
    
    if not check_ffmpeg_installed():
        raise ValueError("FFmpeg is not installed")
    
    if not validate_video_file(video_path):
        raise ValueError(f"Invalid video file: {video_path}")
    
    print(f"Extracting audio from video: {video_path}")
    
    try:
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',              # No video
            '-acodec', 'pcm_s16le',  # WAV format
            '-ar', '48000',     # 48kHz sample rate
            '-ac', '2',         # Stereo
            '-y',               # Overwrite
            output_audio_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg failed: {result.stderr}")
        
        print(f"Extracted audio: {output_audio_path}")
        return output_audio_path
        
    except Exception as e:
        print(f"Error extracting audio: {e}")
        raise


def get_video_duration(video_path: str) -> Optional[float]:
    """
    Gets the duration of a video file in seconds using FFmpeg.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Duration in seconds, or None if unable to determine
    """
    if not check_ffmpeg_installed() or not validate_video_file(video_path):
        return None
    
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return float(result.stdout.strip())
        return None
        
    except Exception:
        return None
