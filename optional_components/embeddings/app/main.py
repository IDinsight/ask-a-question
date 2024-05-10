from typing import List

from config import HUGGINGFACE_MODEL, API_KEY
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from torch import Tensor
from transformers import AutoConfig, AutoModel, AutoTokenizer

app = FastAPI()

security = HTTPBearer()


@app.on_event("startup")
def load_model():
    """Load the model and tokenizer on startup"""
    global tokenizer
    global model
    tokenizer = AutoTokenizer.from_pretrained(HUGGINGFACE_MODEL)
    config = AutoConfig.from_pretrained(HUGGINGFACE_MODEL)
    model = AutoModel.from_pretrained(HUGGINGFACE_MODEL, config=config)
    model.eval()


class RequestModel(BaseModel):
    input: str
    model_name: str = HUGGINGFACE_MODEL


class ResponseModel(BaseModel):
    object: str = "list"
    data: List[dict]
    model_name: str = HUGGINGFACE_MODEL


def average_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    """
    Compute the average pooling of the last hidden states.
    """
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


def verify_token(http_auth: HTTPAuthorizationCredentials = Depends(security)):
    """
    Authenticate using basic bearer token. Used for calling
    the embedding endpoints.
    """
    if http_auth.credentials != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authentication credentials",
        )
    return http_auth.credentials


@app.post("/embeddings", response_model=ResponseModel)
async def get_embeddings(
    request_model: RequestModel, token: str = Depends(verify_token)
):
    """Endpoint to get embeddings for the given text."""
    batch_dict = tokenizer(
        request_model.input,
        max_length=512,
        padding=True,
        truncation=True,
        return_tensors="pt",
    )
    outputs = model(**batch_dict)
    embeddings = average_pool(outputs.last_hidden_state, batch_dict["attention_mask"])

    response_dict = {
        "object": "embedding",
        "index": 0,
        "embedding": embeddings.tolist()[0],
    }
    return ResponseModel(data=[response_dict])


@app.post("/chat/completions", response_model=ResponseModel)
async def get_completions(token: str = Depends(verify_token)):
    """Get chat completions. Required for LiteLLM endpoints"""
    return JSONResponse(status_code=200, content={"status": "ok"})
