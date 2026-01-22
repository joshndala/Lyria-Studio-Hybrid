"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  Music,
  Disc,
  ExternalLink,
  Video,
  Upload,
  CheckCircle,
} from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  audioUrl?: string;
  videoUrl?: string;
  details?: string;
  filename?: string;
  promptRef?: string;
  musicPrompt?: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadedVideo, setUploadedVideo] = useState<File | null>(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string>("");
  const [processingStage, setProcessingStage] = useState<string>("");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [outputType, setOutputType] = useState<"merged" | "audio_only">("merged");

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);


  const handleSend = async () => {
    if (!input.trim()) return;

    const originalPrompt = input;
    const userMsg: Message = {
      role: "user",
      content: originalPrompt
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

      // Generate music with single prompt
      const response = await fetch(`${apiUrl}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: originalPrompt,
        }),
      });

      if (!response.ok) throw new Error("Error generating audio");

      const contentDisposition = response.headers.get("content-disposition");
      let filename = "";
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      const blob = await response.blob();
      const audioUrl = URL.createObjectURL(blob);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Here is your generated track:",
          audioUrl: audioUrl,
          details: "30s • 48kHz stereo",
          filename: filename,
          promptRef: originalPrompt,
        },
      ]);
    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error connecting to Lyria Backend." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleVideoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('video/')) {
        alert('Please select a valid video file (MP4, MOV, etc.)');
        return;
      }

      // Validate file size (100MB limit)
      const maxSize = 100 * 1024 * 1024; // 100MB
      if (file.size > maxSize) {
        alert('Video file is too large. Maximum size is 100MB.');
        return;
      }

      setUploadedVideo(file);
      const previewUrl = URL.createObjectURL(file);
      setVideoPreviewUrl(previewUrl);
    }
  };

  const handleVideoToMusic = async () => {
    if (!uploadedVideo) return;

    const userMsg: Message = {
      role: "user",
      content: `Video uploaded: ${uploadedVideo.name}`,
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setProcessingStage("uploading");
    setStatusMessage("Uploading video to server...");

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

      // Create form data
      const formData = new FormData();
      formData.append('video', uploadedVideo);

      // Update status: Analyzing
      setTimeout(() => {
        setProcessingStage("analyzing");
        setStatusMessage("Analyzing video with Gemini AI...");
      }, 500);

      // Simulate progress updates
      setTimeout(() => {
        setStatusMessage("Waiting for video processing to complete...");
      }, 2000);

      setTimeout(() => {
        setProcessingStage("generating");
        setStatusMessage("Generating music with Lyria 2...");
      }, 5000);

      if (outputType === "merged") {
        setTimeout(() => {
          setProcessingStage("merging");
          setStatusMessage("Merging audio with video...");
        }, 25000);
      }

      const response = await fetch(`${apiUrl}/video-to-music?output_type=${outputType}`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Error processing video");
      }

      // Get the music prompt from headers
      const musicPrompt = response.headers.get("X-Music-Prompt") || "Generated music";

      // Get the video blob
      const blob = await response.blob();
      const videoUrl = URL.createObjectURL(blob);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Here is your video with generated music:",
          videoUrl: videoUrl,
          details: "Video with AI-generated soundtrack",
          filename: `video_with_music_${Date.now()}.mp4`,
          musicPrompt: musicPrompt,
        },
      ]);

      // Clear video upload state
      setUploadedVideo(null);
      setVideoPreviewUrl("");

    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error processing video: ${error instanceof Error ? error.message : 'Unknown error'}`
        },
      ]);
    } finally {
      setLoading(false);
      setProcessingStage("");
    }
  };

  return (
    <div className="flex flex-col h-screen bg-white text-gray-900 font-sans overflow-hidden">
      <header className="p-4 border-b border-gray-200 flex items-center gap-2 bg-white/80 backdrop-blur z-10 sticky top-0 shadow-sm">
        <Disc className="text-[#5B3890] animate-spin-slow" />
        <h1 className="font-bold text-lg tracking-tight bg-gradient-to-r from-[#5B3890] to-[#7B5AA0] bg-clip-text text-transparent">
          Lyria Studio V2
        </h1>
        <span className="text-[10px] font-medium bg-[#5B3890]/10 text-[#5B3890] px-2 py-0.5 rounded-full border border-[#5B3890]/20 uppercase tracking-wide">
          Beta
        </span>
      </header>

      <div className="flex-1 overflow-y-auto p-6 space-y-4 relative scroll-smooth bg-gray-50">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-gray-500 space-y-6 animate-in fade-in zoom-in duration-500">
            <div className="relative">
              <div className="absolute inset-0 bg-[#5B3890]/10 blur-3xl rounded-full"></div>
              <Music size={64} className="relative opacity-30 text-[#5B3890]" />
            </div>
            <div className="text-center space-y-2">
              <p className="text-lg font-semibold text-gray-800">
                Describe the music you want to create
              </p>
              <p className="text-sm text-gray-500">
                Our AI engine will compose it in seconds.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setInput("A synthwave track with heavy bass")}
                className="text-xs text-gray-700 hover:text-[#5B3890] bg-white hover:bg-gray-50 px-4 py-2 rounded-full border border-gray-200 hover:border-[#5B3890] transition-all shadow-sm"
              >
                "Synthwave track"
              </button>
              <button
                onClick={() => setInput("Lo-fi hip hop beat for studying")}
                className="text-xs text-gray-700 hover:text-[#5B3890] bg-white hover:bg-gray-50 px-4 py-2 rounded-full border border-gray-200 hover:border-[#5B3890] transition-all shadow-sm"
              >
                "Lo-fi beat"
              </button>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"
              } animate-in slide-in-from-bottom-2 duration-300`}
          >
            <div
              className={`
                p-5 rounded-2xl shadow-sm
                ${msg.role === "user"
                  ? "bg-white text-gray-900 border border-gray-200 max-w-[85%]"
                  : "bg-white border border-gray-200 w-full max-w-[95%] sm:max-w-[600px]"
                }
              `}
            >
              <p className="text-sm mb-3 font-medium leading-relaxed text-gray-800">
                {msg.content}
              </p>

              {msg.audioUrl && (
                <div className="mt-4 bg-gray-50 p-4 rounded-xl border border-gray-200">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="flex-1 h-10 bg-white rounded-lg overflow-hidden flex items-center px-2 border border-gray-200">
                      <audio
                        controls
                        src={msg.audioUrl}
                        className="w-full h-full block"
                        preload="metadata"
                      />
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-3 border-t border-gray-200">
                    {msg.details && (
                      <div className="flex flex-col">
                        <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">
                          Parameters
                        </span>
                        <span className="text-xs text-gray-700 font-mono">
                          {msg.details}
                        </span>
                      </div>
                    )}

                    <a
                      href={`http://localhost:8501?file=${msg.filename || ""
                        }&prompt=${encodeURIComponent(
                          msg.promptRef || "Imported Audio"
                        )}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group flex items-center gap-2 text-xs bg-[#5B3890] hover:bg-[#6D4D9C] text-white pl-4 pr-3 py-2 rounded-lg transition-all shadow-sm hover:shadow-md"
                    >
                      <span className="font-semibold">Open in Studio</span>
                      <ExternalLink
                        size={14}
                        className="transition-colors"
                      />
                    </a>
                  </div>
                </div>
              )}

              {msg.videoUrl && (
                <div className="mt-4 bg-gray-50 p-4 rounded-xl border border-gray-200">
                  <div className="mb-3">
                    <video
                      controls
                      src={msg.videoUrl}
                      className="w-full rounded-lg border border-gray-200"
                      preload="metadata"
                    />
                  </div>

                  <div className="flex justify-between items-center pt-3 border-t border-gray-200">
                    <div className="flex flex-col gap-1">
                      {msg.details && (
                        <div className="flex flex-col">
                          <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">
                            Type
                          </span>
                          <span className="text-xs text-gray-700 font-mono">
                            {msg.details}
                          </span>
                        </div>
                      )}
                      {msg.musicPrompt && (
                        <div className="flex flex-col mt-2">
                          <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">
                            Music Prompt
                          </span>
                          <span className="text-xs text-gray-700 italic">
                            {msg.musicPrompt}
                          </span>
                        </div>
                      )}
                    </div>

                    <a
                      href={msg.videoUrl}
                      download={msg.filename}
                      className="group flex items-center gap-2 text-xs bg-[#5B3890] hover:bg-[#6D4D9C] text-white pl-4 pr-3 py-2 rounded-lg transition-all shadow-sm hover:shadow-md"
                    >
                      <span className="font-semibold">Download Video</span>
                      <Upload
                        size={14}
                        className="transition-colors rotate-180"
                      />
                    </a>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start animate-pulse">
            <div className="bg-white border border-gray-200 p-4 rounded-2xl shadow-sm">
              <div className="flex items-center gap-3 text-gray-700 text-sm">
                <div className="flex gap-1">
                  <div
                    className="w-2 h-2 bg-[#5B3890] rounded-full animate-bounce"
                    style={{ animationDelay: "0ms" }}
                  />
                  <div
                    className="w-2 h-2 bg-[#5B3890] rounded-full animate-bounce"
                    style={{ animationDelay: "150ms" }}
                  />
                  <div
                    className="w-2 h-2 bg-[#5B3890] rounded-full animate-bounce"
                    style={{ animationDelay: "300ms" }}
                  />
                </div>
                <span className="font-medium">
                  {processingStage === "analyzing"
                    ? "Analyzing video mood and pacing..."
                    : processingStage === "generating"
                      ? "Generating music track..."
                      : processingStage === "merging"
                        ? "Merging audio with video..."
                        : "Composing track..."}
                </span>
              </div>
              {processingStage && (
                <div className="mt-3 flex gap-2">
                  <div className={`flex items-center gap-1 text-xs ${processingStage === "analyzing" ? "text-[#5B3890] font-semibold" : "text-gray-500"}`}>
                    {processingStage !== "analyzing" && <CheckCircle size={12} />}
                    <span>Analyze</span>
                  </div>
                  <span className="text-gray-400">→</span>
                  <div className={`flex items-center gap-1 text-xs ${processingStage === "generating" ? "text-[#5B3890] font-semibold" : "text-gray-500"}`}>
                    {processingStage === "merging" && <CheckCircle size={12} />}
                    <span>Generate</span>
                  </div>
                  <span className="text-gray-400">→</span>
                  <div className={`flex items-center gap-1 text-xs ${processingStage === "merging" ? "text-[#5B3890] font-semibold" : "text-gray-500"}`}>
                    <span>Merge</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-white border-t border-gray-200 relative z-20 shadow-lg">
        {/* Video Upload Preview */}
        {uploadedVideo && videoPreviewUrl && (
          <div className="max-w-4xl mx-auto mb-3 bg-gray-50 border border-gray-200 rounded-xl p-4">
            <div className="flex items-center gap-4">
              <video
                src={videoPreviewUrl}
                className="w-32 h-20 object-cover rounded-lg border border-gray-200"
                muted
              />
              <div className="flex-1">
                <p className="text-sm text-gray-900 font-medium">{uploadedVideo.name}</p>
                <p className="text-xs text-gray-500">
                  {(uploadedVideo.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <button
                onClick={() => {
                  setUploadedVideo(null);
                  setVideoPreviewUrl("");
                }}
                className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
              >
                Remove
              </button>
            </div>

            {/* Output Type Selection */}
            <div className="mt-3 mb-3">
              <p className="text-xs text-gray-600 font-semibold mb-2">Output Type:</p>
              <div className="flex gap-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="outputType"
                    value="merged"
                    checked={outputType === "merged"}
                    onChange={(e) => setOutputType(e.target.value as "merged" | "audio_only")}
                    className="w-4 h-4 text-[#5B3890] focus:ring-[#5B3890] focus:ring-2"
                  />
                  <span className="text-sm text-gray-700">Video with Music</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="outputType"
                    value="audio_only"
                    checked={outputType === "audio_only"}
                    onChange={(e) => setOutputType(e.target.value as "merged" | "audio_only")}
                    className="w-4 h-4 text-[#5B3890] focus:ring-[#5B3890] focus:ring-2"
                  />
                  <span className="text-sm text-gray-700">Music Only</span>
                </label>
              </div>
            </div>

            <button
              onClick={handleVideoToMusic}
              disabled={loading}
              className="w-full bg-[#5B3890] hover:bg-[#6D4D9C] disabled:opacity-50 text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-all flex items-center justify-center gap-2 shadow-sm"
            >
              <Music size={16} />
              {outputType === "merged" ? "Generate Music for Video" : "Generate Music from Video"}
            </button>
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="relative max-w-4xl mx-auto flex gap-3 items-end"
        >

          <div className="flex-1 relative group">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe the music you want to create..."
              className="w-full bg-white border border-gray-300 group-hover:border-[#5B3890] rounded-xl px-5 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B3890]/20 focus:border-[#5B3890] transition-all placeholder:text-gray-400 text-gray-900"
              disabled={loading}
            />
          </div>

          {/* Video Upload Button */}
          <label className="bg-gray-200 hover:bg-[#5B3890] hover:text-white text-gray-700 disabled:opacity-50 p-3.5 rounded-xl transition-all shadow-sm cursor-pointer active:scale-95">
            <input
              type="file"
              accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska"
              onChange={handleVideoUpload}
              className="hidden"
              disabled={loading}
            />
            <Video size={20} />
          </label>

          <button
            type="submit"
            disabled={loading || !input}
            className="bg-[#5B3890] hover:bg-[#6D4D9C] disabled:opacity-50 disabled:cursor-not-allowed text-white p-3.5 rounded-xl transition-all shadow-sm hover:shadow-md active:scale-95"
          >
            <Send size={20} fill="currentColor" className="ml-0.5" />
          </button>
        </form>
      </div>
    </div>
  );
}
