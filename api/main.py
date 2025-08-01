from fastapi import FastAPI

app = FastAPI()

@app.get("/api/main")
def main_endpoint():
    return {"message": "Hello from main.py", "file": "main.py"}