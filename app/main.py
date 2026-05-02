from fastapi import FastAPI


app = FastAPI(
    title="FastAPI E-Commerce Backend",
    description="A simple FastAPI E-Commerce application",
    version="1.0.0"
)


@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI E-Commerce Backend!"}
