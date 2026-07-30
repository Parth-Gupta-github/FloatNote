/**
 * Marketing content, kept out of the components so copy is easy to tune
 * and can also feed structured data (FAQ schema) from a single source.
 */

export const features = [
  {
    icon: "mic",
    title: "Mic & System Audio Capture",
    description:
      "Streams audio from your mic and remote participants (via Windows WASAPI loopback) through OpenAI Whisper base model, gated by Silero VAD for real-time speech detection.",
  },
  {
    icon: "screen",
    title: "Screen OCR",
    description:
      "Reads slides and shared screens as they change via Tesseract OCR, extracting on-screen text and keywords so your meeting notes capture what was shown.",
  },
  {
    icon: "sparkles",
    title: "AI Summarization",
    description:
      "Turns meeting recordings into structured summaries using Qwen2.5-7B via Hugging Face Inference Providers, with a local fallback when offline.",
  },
  {
    icon: "chat",
    title: "Meeting Chatbot",
    description:
      "Ask questions about any past meeting. Answers are grounded in a local FAISS vector store via retrieval-augmented generation (RAG) — no hallucinated recaps.",
  },
  {
    icon: "speakers",
    title: "Speaker Diarization",
    description:
      "Runs fully offline — streaming Resemblyzer d-vector embeddings cluster utterances in real time, assigning consistent speaker labels (SPEAKER_00 / SPEAKER_01) across the live call.",
  },
  {
    icon: "check",
    title: "Action Item Extraction",
    description:
      "An NLP pipeline (spaCy) detects tasks and who they're assigned to straight from spoken language — so nothing agreed on gets lost.",
  },
  {
    icon: "database",
    title: "Persistent Local Memory",
    description:
      "Transcripts, speaker aliases, OCR captures, and action items are saved locally to SQLite via async SQLAlchemy — searchable meeting memory on your machine.",
  },
] as const;

export const steps = [
  {
    number: "01",
    title: "It runs in the background",
    description:
      "Launch FloatNote and it quietly captures your mic, system audio, and shared slides. No bot joins the call, no awkward 'recording started' banner.",
  },
  {
    number: "02",
    title: "Everything becomes memory",
    description:
      "Speech becomes transcript, slides become text, and both are indexed into a local FAISS vector store as the meeting happens.",
  },
  {
    number: "03",
    title: "Ask it anything, after",
    description:
      "Get an instant AI summary, pull the action items, or chat with the meeting — 'What action items were assigned to me?' — and get grounded answers.",
  },
] as const;

export const useCases = [
  {
    title: "Product & engineering",
    description:
      "Capture roadmap debates and design decisions with the slides that drove them. Query 'why did we pick Postgres?' six weeks later.",
  },
  {
    title: "Sales & customer calls",
    description:
      "Never scribble notes mid-call again. Get the summary, the commitments, and the follow-ups extracted automatically from mic and loopback audio.",
  },
  {
    title: "Research & interviews",
    description:
      "Transcribe user interviews verbatim with speaker labels, then chat across every session to find patterns without re-watching recordings.",
  },
  {
    title: "Students & lectures",
    description:
      "Record lectures with the on-screen slides captured via Tesseract OCR, then ask the chatbot to explain any concept from class.",
  },
] as const;

export const techStack = [
  { name: "FastAPI", role: "Async server + WebSockets" },
  { name: "Whisper + Silero VAD", role: "Local speech-to-text & VAD" },
  { name: "WASAPI Loopback", role: "Mic & system audio capture" },
  { name: "Resemblyzer", role: "Offline speaker diarization" },
  { name: "Tesseract OCR", role: "Screen & slide reading" },
  { name: "Qwen2.5-7B (HuggingFace)", role: "Summaries, chat & keywords" },
  { name: "LangChain + FAISS", role: "RAG retrieval pipeline" },
  { name: "spaCy NLP", role: "Action item extraction" },
  { name: "SQLite + SQLAlchemy", role: "Local persistent storage" },
  { name: "React 19 + Vite", role: "Dashboard UI" },
  { name: "Electron", role: "Desktop app wrapper" },
] as const;

export const faqs = [
  {
    question: "Does my audio get sent to the cloud?",
    answer:
      "Transcription (Whisper), VAD (Silero), speaker diarization (Resemblyzer), and RAG vector storage (FAISS) all run locally on your machine. Transcripts and meeting data stay in a local SQLite database. Summaries and the chatbot use Hugging Face Inference Providers (Qwen2.5-7B), so only text you choose to query or summarize is sent.",
  },
  {
    question: "Do I have to invite a bot to my meeting?",
    answer:
      "No. FloatNote captures your microphone and system audio (via Windows WASAPI loopback) and reads your screen directly from your desktop. There's no meeting bot, no join link, and no participant to explain — it runs quietly in the background.",
  },
  {
    question: "What can the meeting chatbot actually answer?",
    answer:
      "Anything grounded in the meeting. It uses retrieval-augmented generation (RAG) over a local FAISS vector store of your transcript and OCR captures, surfacing decisions, action items, and context tied to what was actually said or shown.",
  },
  {
    question: "Which platforms does it run on?",
    answer:
      "FloatNote is desktop-first, built with a FastAPI backend and a React dashboard, with an optional Electron wrapper for a native window. Windows is required for system audio loopback capture; mic-only capture works on all platforms.",
  },
  {
    question: "Is it free and open source?",
    answer:
      "Yes. FloatNote is open source — you run it yourself with a Hugging Face API token for AI summaries and chat (with a local fallback if no token is provided). The full source code, architecture, and setup instructions are on GitHub.",
  },
] as const;

export const stats = [
  { value: "Real-time", label: "Live transcription & VAD" },
  { value: "100%", label: "Transcripts stored locally" },
  { value: "0", label: "Meeting bots to invite" },
  { value: "Open", label: "Source, self-hosted" },
] as const;
