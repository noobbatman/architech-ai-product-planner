from fastapi import FastAPI
from api.v1 import projects as projects_v1

app = FastAPI(
    title="ArchiTECH API",
    description="The full-scale API for ArchiTECH.",
    version="1.0.0"
)

# Mount the v1 API router
app.include_router(projects_v1.router, prefix="/api/v1/projects", tags=["Projects"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the ArchiTECH API"}