import os
import warnings

warnings.filterwarnings(
    "ignore",
    message="TypedStorage is deprecated"
)

try:
    from ai_modules.stt.whisper_engine import run_server
except Exception as e:
    print(f"⚠️ STT backend import failed: {e}")
    from fastapi import FastAPI
    import uvicorn

    app = FastAPI()

    @app.get("/")
    def root():
        return {
            "status": "dev-fallback",
            "message": "STT disabled; install full requirements to enable full features",
        }

    def run_server(host: str = "0.0.0.0", port: int = 8000):
        uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    print("🌐 Running Server...\n")
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    run_server(host=host, port=port)
