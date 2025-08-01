from fastapi import FastAPI

app = FastAPI()

@app.get("/api")
def hello_world():
    return {"message": "Hello from FastAPI"}

@app.get("/api/python")
def hello_python():
    return {"message": "Hello from Python"}