# GreenFund-test-Backend/app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_db_and_tables
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.farms import router as farms_router
from app.routers.climate import router as climate_router
from app.routers.activities import router as activities_router
from app.routers.soil import router as soil_router
from app.routers.test_router import router as test_router
from app.routers.forum import router as forum_router # Import forum router
from app.routers.climate_actions import router as climate_actions_router # Import climate actions router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up and creating database tables...")
    create_db_and_tables() # This will now create the forum tables too
    yield
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

# CORS Middleware Configuration
origins = [
    "http://localhost",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all the routers with their respective prefixes
app.include_router(auth_router, prefix="/api/auth")
app.include_router(users_router, prefix="/api/users")
app.include_router(farms_router, prefix="/api")
app.include_router(climate_router, prefix="/api")
app.include_router(activities_router, prefix="/api")
app.include_router(soil_router, prefix="/api")
app.include_router(forum_router, prefix="/api") # Include the forum router
app.include_router(climate_actions_router, prefix="/api") # Include climate actions router
app.include_router(test_router) # Test router has prefix defined inside it

@app.get("/")
def read_root():
    return {"message": "Welcome to the GreenFund API"}