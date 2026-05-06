from decouple import config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.account.routers import router as account_router
from app.product.routers.category_router import router as category_router
from app.product.routers.product_router import router as product_router
from app.cart.routers import router as cart_router
from app.shipping.routers import router as shipping_router


app = FastAPI(
    title="FastAPI E-Commerce Backend",
    description="A simple FastAPI E-Commerce application",
    version="1.0.0",
)


app.mount("/media", StaticFiles(directory="media"), name="media")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config("FRONTEND_URL")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Welcome to the E-Commerce API"}


app.include_router(account_router, prefix="/api/account", tags=["Account"])
app.include_router(product_router, prefix="/api/products", tags=["Products"])
app.include_router(
    category_router, prefix="/api/products-category", tags=["Product Categories"]
)
app.include_router(cart_router, prefix="/api/carts", tags=["Carts"])
app.include_router(shipping_router, prefix="/api/shippings", tags=["Shippings"])