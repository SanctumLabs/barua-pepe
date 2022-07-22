import uvicorn
import os

port = os.environ.get("PORT", 5000)
reload = os.environ.get("ENV", "development") == "development"

if __name__ == "__main__":
    uvicorn.run("app:app", port=port, reload=reload)
