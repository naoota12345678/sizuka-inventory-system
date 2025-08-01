from fastapi import FastAPI
from fastapi.responses import Response

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)