from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI()
class User(BaseModel):
    name: str
@app.post("/users")
def create(user: User):
    return {"created": user.name}
