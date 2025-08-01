from fastapi import FastAPI

app = FastAPI()

@app.get("/api")
def hello_world():
    return {
        "message": "Hello from FastAPI",
        "endpoints": ["/api", "/api/python", "/api/test"]
    }

@app.get("/api/python")
def hello_python():
    return {"message": "Hello from Python", "status": "working"}

@app.get("/api/test")
def test_endpoint():
    return {"message": "Test endpoint", "timestamp": "2025-01-01"}