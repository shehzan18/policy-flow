from fastapi import FastAPI, Request
app = FastAPI()
@app.post("/users")
async def create(request: Request):
    data = await request.json()
    return {"created": data["name"]}
