from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from routers import bins, routes, security, energy, ws, truck, commands, agent, sim, admin_demo
from services.truck_simulator import start_truck_simulator, stop_truck_simulator


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    truck_task = start_truck_simulator()
    try:
        yield
    finally:
        await stop_truck_simulator(truck_task)


app = FastAPI(
    title="Smarte Mülltonne API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?$",
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
app.include_router(admin_demo.router, prefix="/admin/demo", tags=["admin-demo"])
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
