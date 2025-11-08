from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Import CORSMiddleware
from api.v1 import projects as projects_v1

app = FastAPI(
    title="ArchiTECH API",
    description="The full-scale API for ArchiTECH.",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allows requests from your frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allows all standard methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Mount the v1 API router
app.include_router(projects_v1.router, prefix="/api/v1/projects", tags=["Projects"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the ArchiTECH API"}