import uvicorn
from fastapi import FastAPI
from pprl_model import HealthResponse

from pprl_service.routers import match, transform, mask

app = FastAPI()
app.include_router(match.router, prefix="/match")
app.include_router(transform.router, prefix="/transform")
app.include_router(mask.router, prefix="/mask")


@app.get("/healthz", response_model=HealthResponse)
async def get_health():
    return HealthResponse()


def run_server():
    uvicorn.run(app)


if __name__ == "__main__":
    run_server()
