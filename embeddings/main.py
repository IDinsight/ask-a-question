import os
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from torch import Tensor
from torch import nn
from transformers import AutoConfig, AutoModel, AutoTokenizer

app = FastAPI(port=8081, debug=True)

HUGGINGFACE_MODEL = os.environ.get("HUGGINGFACE_MODEL", "thenlper/gte-large")

security = HTTPBearer()
STATIC_TOKEN = "question"


@app.on_event("startup")
def load_model():
    global tokenizer
    global model
    tokenizer = AutoTokenizer.from_pretrained(HUGGINGFACE_MODEL)
    config = AutoConfig.from_pretrained(HUGGINGFACE_MODEL)
    model = AutoModel.from_pretrained(HUGGINGFACE_MODEL, config=config)
    model.eval()


class EmbeddingProjector(nn.Module):
    def __init__(self, original_dim, target_dim=1536):
        super().__init__()
        # Define a linear layer to project from original_dim to target_dim
        self.projection = nn.Linear(original_dim, target_dim)

    def forward(self, x):
        return self.projection(x)


class RequestModel(BaseModel):
    input: str
    model_name: str = HUGGINGFACE_MODEL


class ResponseModel(BaseModel):
    object: str = "list"
    data: List[dict]
    model_name: str = HUGGINGFACE_MODEL


def average_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


def verify_token(http_auth: HTTPAuthorizationCredentials = Depends(security)):
    if http_auth.credentials != STATIC_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authentication credentials",
        )
    return http_auth.credentials


@app.post("/embeddings", response_model=ResponseModel)
async def complete(request_model: RequestModel, token: str = Depends(verify_token)):

    batch_dict = tokenizer(
        request_model.input,
        max_length=1536,
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
async def complete(token: str = Depends(verify_token)):
    return JSONResponse(status_code=200, content={"status": "ok"})
