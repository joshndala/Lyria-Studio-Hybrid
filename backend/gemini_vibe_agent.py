import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"  # Using latest Gemini 2.0 flash model

def _build_film_scorer_prompt() -> str:
    """Returns the system prompt for the Gemini film scorer agent."""
    return """You are a professional film scorer with decades of experience in composing music for visual media.

Your task is to watch this video and analyze its mood, pacing, energy, and emotional tone. Based on your analysis, output a SINGLE, descriptive text prompt that is optimized for a music generation AI model (Lyria).

CRITICAL INSTRUCTIONS TO AVOID CONTENT FILTERS:
- Be EXTREMELY SPECIFIC with technical music production details
- Include exact BPM, key signature, time signature
- Describe specific instrument combinations and sound design techniques
- Use technical audio engineering terms (compression, reverb, EQ, etc.)
- Avoid generic phrases like "upbeat", "energetic", "motivating" alone
- Instead use: "staccato rhythms", "legato phrasing", "syncopated patterns"
- Do NOT describe the visuals or what you see in the video
- DO describe the music that would perfectly fit the video
- Do NOT mention specific artist names or copyrighted song titles
- Describe the instruments, tempo, and emotional texture only

EXAMPLE OUTPUT FORMAT (HIGHLY SPECIFIC):
"Instrumental composition in A minor, 128 BPM, 4/4 time signature, featuring layered analog synthesizers with sawtooth waveforms, punchy TR-808 style kick drums with side-chain compression, arpeggiated bassline with filter sweeps, bright pad textures with reverb tail, syncopated hi-hat patterns, and dynamic build-ups using white noise risers"

OR

"Acoustic arrangement in D major, 72 BPM, 3/4 waltz time, with fingerpicked steel-string guitar using DADGAD tuning, soft brush drums on snare, upright bass playing walking patterns, subtle string quartet harmonies in the background, gentle piano countermelodies, creating a contemplative and introspective atmosphere"

Now analyze the video and provide your HIGHLY SPECIFIC music prompt with technical details:"""


async def analyze_video_for_music(video_path: str) -> str:
    """
    Analyzes a video file using Gemini 1.5 Pro to generate a music prompt.
    
    Args:
        video_path: Path to the video file to analyze
        
    Returns:
        A text prompt optimized for music generation
        
    Raises:
        ValueError: If API key is missing or video file is invalid
        Exception: If Gemini API call fails
    """
    
    # Validate API key
    if not GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY not found in environment variables. "
            "Please add it to your .env file."
        )
    
    # Validate video file exists
    if not os.path.exists(video_path):
        raise ValueError(f"Video file not found: {video_path}")
    
    print(f"Analyzing video with Gemini 1.5 Pro: {video_path}")
    
    try:
        # Configure Gemini API
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # Initialize the model
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # Upload the video file
        print("Uploading video to Gemini...")
        video_file = genai.upload_file(path=video_path)
        
        # Wait for the file to be processed
        print("Processing video...")
        
        # Poll until the file is in ACTIVE state
        import time
        max_wait_time = 120  # 2 minutes max wait
        poll_interval = 2  # Check every 2 seconds
        elapsed_time = 0
        
        while video_file.state.name != "ACTIVE":
            if elapsed_time >= max_wait_time:
                raise Exception(f"File processing timeout after {max_wait_time} seconds")
            
            print(f"Waiting for file to be processed... (state: {video_file.state.name})")
            time.sleep(poll_interval)
            elapsed_time += poll_interval
            
            # Refresh file state
            video_file = genai.get_file(video_file.name)
        
        print(f"File is ready (state: {video_file.state.name})")
        
        # Build the prompt
        prompt = _build_film_scorer_prompt()
        
        # Generate content with video and prompt
        print("Generating music prompt from video analysis...")
        response = model.generate_content(
            [video_file, prompt],
            request_options={"timeout": 120}  # 2 minute timeout for video processing
        )
        
        # Extract the music prompt from response
        music_prompt = response.text.strip()
        
        # Clean up: delete the uploaded file from Gemini
        try:
            genai.delete_file(video_file.name)
        except:
            pass  # Non-critical if cleanup fails
        
        print(f"Generated music prompt: {music_prompt}")
        return music_prompt
        
    except Exception as e:
        print(f"Error in Gemini video analysis: {e}")
        raise Exception(f"Failed to analyze video with Gemini: {str(e)}")


async def analyze_prompt_for_negative(user_prompt: str) -> str:
    """
    Analyzes a user's music generation prompt to determine if a negative prompt would be beneficial.
    
    Args:
        user_prompt: The user's original music generation prompt
        
    Returns:
        A suggested negative prompt string, or empty string if not needed
    """
    
    # Validate API key
    if not GOOGLE_API_KEY:
        print("Warning: GOOGLE_API_KEY not found, skipping negative prompt analysis")
        return ""
    
    try:
        # Configure Gemini API
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # Initialize the model
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # Build the analysis prompt
        analysis_prompt = f"""You are an expert music production assistant. Analyze the following music generation prompt and determine if a negative prompt would improve the quality of the generated music.

User's prompt: "{user_prompt}"

Your task:
1. Identify if the user is asking for specific qualities that might benefit from excluding opposite qualities
2. Common cases where negative prompts help:
   - "calm/peaceful" music → exclude: loud, aggressive, harsh
   - "instrumental" → exclude: vocals, singing, lyrics
   - "clean production" → exclude: distortion, noise, lo-fi
   - "acoustic" → exclude: electronic, synthesized
   - "slow/relaxing" → exclude: fast, energetic, intense

3. Return ONLY a concise negative prompt (comma-separated unwanted elements), or return "NONE" if a negative prompt is not needed.

Examples:
- User: "calm ambient music" → Response: "loud, aggressive, distorted, harsh, intense"
- User: "instrumental jazz piano" → Response: "vocals, singing, lyrics, speech"
- User: "energetic rock with distorted guitars" → Response: "NONE"
- User: "clean electronic beat" → Response: "noise, artifacts, distortion, lo-fi"

Your response (negative prompt or NONE):"""

        # Generate the analysis
        response = model.generate_content(
            analysis_prompt,
            request_options={"timeout": 10}
        )
        
        # Extract and clean the response
        negative_prompt = response.text.strip()
        
        # If the model says NONE or similar, return empty string
        if negative_prompt.upper() in ["NONE", "N/A", "NOT NEEDED", "NO", ""]:
            print(f"No negative prompt needed for: {user_prompt}")
            return ""
        
        print(f"Suggested negative prompt for '{user_prompt}': {negative_prompt}")
        return negative_prompt
        
    except Exception as e:
        print(f"Error analyzing prompt for negative: {e}")
        # Fail gracefully - don't block music generation
        return ""


async def analyze_video_for_music_with_fallback(video_path: str, fallback_prompt: str = None) -> str:
    """
    Analyzes video with Gemini, with optional fallback prompt if analysis fails.
    
    Args:
        video_path: Path to the video file
        fallback_prompt: Optional fallback prompt if Gemini fails
        
    Returns:
        Music prompt from Gemini or fallback
    """
    try:
        return await analyze_video_for_music(video_path)
    except Exception as e:
        print(f"Gemini analysis failed: {e}")
        if fallback_prompt:
            print(f"Using fallback prompt: {fallback_prompt}")
            return fallback_prompt
        else:
            # Use a highly specific, original fallback to avoid recitation filter
            # This prompt is unique and won't match any copyrighted content
            fallback = "Energetic instrumental composition at 128 BPM featuring layered analog synthesizers, punchy electronic drums with side-chain compression, arpeggiated bassline in D minor, bright pad textures, and rhythmic hi-hat patterns creating an uplifting modern electronic atmosphere"
            print(f"Using safe fallback prompt: {fallback}")
            return fallback
