from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Multi-Agent Support Assistant")
app.include_router(router)
