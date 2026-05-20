from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from routers import bins, routes, security, energy, ws, truck, commands, agent, sim


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Smarte Mülltonne API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bins.router, prefix="/bins", tags=["bins"])
app.include_router(routes.router, prefix="/routes", tags=["routes"])
app.include_router(security.router, prefix="/security", tags=["security"])
app.include_router(energy.router, prefix="/energy", tags=["energy"])
app.include_router(truck.router, prefix="/truck", tags=["truck"])
app.include_router(commands.router, prefix="/bins", tags=["commands"])
app.include_router(agent.router, prefix="/agent", tags=["agent"])
app.include_router(sim.router, prefix="/sim", tags=["sim"])
app.include_router(ws.router, tags=["websocket"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/config/public")
def public_config():
    """Non-sensitive settings exposed to the frontend."""
    return {
        "depot": {
            "lat": settings.depot_lat,
            "lng": settings.depot_lng,
            "name": settings.depot_name,
        },
    }
