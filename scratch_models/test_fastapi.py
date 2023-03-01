from fastapi import FastAPI
from fastapi import Form
from models.model_virtualSource import VirtualSource
from models.model_virtualSource import vsources

# imports indirectly needed: uvicorn, python-multipart, jinja2

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/vs_item/{item_id}")
async def read_item(item_id: str):
    return VirtualSource(name=item_id).dict()


@app.get("/vs_items")
async def read_items(skip: int = 0, limit: int = 40):
    return {"message": list(vsources.keys())[skip : skip + limit]}


@app.post("/vs_set")
async def read_items(item: VirtualSource):
    return item.dict()


@app.post("/login/")
async def login(username: str = Form(), password: str = Form()):
    return {"username": username}


# run with: uvicorn test_fastapi:app --reload
