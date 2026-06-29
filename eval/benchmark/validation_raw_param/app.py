from fastapi import FastAPI
app = FastAPI()
@app.get("/calc")
def calc(value):
    return {"result": int(value) * 2}
