from fastapi import FastAPI

app = FastAPI()

@app.get("/api/python")
def python_endpoint():
    return {"message": "Hello from Python", "status": "working"}