from fastapi import FastAPI

app = FastAPI()

@app.get("/api/hello")
def hello_endpoint():
    return {"message": "Hello from hello.py", "file": "hello.py"}