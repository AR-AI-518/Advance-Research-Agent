from fastapi import FastAPI
from fastapi.responses import JSONResponse

from layers.models import ChatResponse, ErrorResponse, MetricsCollection, UserRequest
from main import Pipeline

app = FastAPI(title="Research Agent API")
pipeline = Pipeline()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: UserRequest):
    thread_id = None if request.thread_id == "Default" else request.thread_id

    try:
        return pipeline.run(request.message, request.user_id, thread_id)
    except ValueError as e:
        error = ErrorResponse(error="bad_request", detail=str(e), user_id=request.user_id)
        return JSONResponse(status_code=400, content=error.model_dump())
    except Exception as e:
        error = ErrorResponse(error="internal_error", detail=str(e), user_id=request.user_id)
        return JSONResponse(status_code=500, content=error.model_dump())


@app.get("/metrics", response_model=MetricsCollection)
def metrics():
    return pipeline.get_metrics()