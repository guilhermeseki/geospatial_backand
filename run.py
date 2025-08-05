# run.py
import uvicorn
from api.main import app

if __name__ == "__main__":
    uvicorn.run(
        app="api.main:app",  # Standard import path format
        host="0.0.0.0",     # Accessible from all network interfaces
        port=8000,          # Default port
        reload=True,        # Enable auto-reload during development
        workers=4           # In production, set based on CPU cores
    )