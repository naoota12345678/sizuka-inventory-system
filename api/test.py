from fastapi import FastAPI

app = FastAPI()

@app.get("/api/test")
def test_endpoint():
    return {"message": "Test endpoint", "timestamp": "2025-01-01"}