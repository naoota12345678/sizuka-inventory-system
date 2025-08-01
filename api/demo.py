from fastapi import FastAPI

app = FastAPI()

@app.get("/api/demo")
def demo_endpoint():
    return {"message": "Demo endpoint", "timestamp": "2025-01-01"}