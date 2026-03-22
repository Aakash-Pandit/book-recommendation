import os
import uvicorn

if __name__ == "__main__":
    dev_mode = os.getenv("APP_ENV", "development") == "development"
    uvicorn.run(
        "application.api:application",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        workers=1 if dev_mode else int(os.getenv("WEB_CONCURRENCY", 2)),
        reload=dev_mode,
    )