from typing import List

from config import API_KEY, HUGGINGFACE_MODEL
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from torch import Tensor
from transformers import AutoConfig, AutoModel, AutoTokenizer

app = FastAPI()

security = HTTPBearer()


@app.on_event("startup")
def load_model():
    """Load the model and tokenizer on startup"""
    app.state.tokenizer = AutoTokenizer.from_pretrained(HUGGINGFACE_MODEL)
    config = AutoConfig.from_pretrained(HUGGINGFACE_MODEL)
    app.state.model = AutoModel.from_pretrained(HUGGINGFACE_MODEL, config=config)
    app.state.model.eval()


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
    request: Request, request_input: RequestModel, token: str = Depends(verify_token)
):
    """Endpoint to get embeddings for the given text."""
    tokenizer = request.app.state.tokenizer
    model = request.app.state.model
    batch_dict = tokenizer(
        request_input.input,
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
