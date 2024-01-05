import os
from functools import lru_cache
from typing import List, Literal

import nltk
import typer
import uvicorn
from alignscore import AlignScore
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Make sure we have the punkt tokenizer downloaded.
nltk.download("punkt")

models_path = os.environ.get("ALIGN_SCORE_PATH")

if models_path is None:
    raise ValueError(
        "Please set the ALIGN_SCORE_PATH environment variable "
        "to point to the AlignScore checkpoints folder. "
    )

app = FastAPI()

device = os.environ.get("ALIGN_SCORE_DEVICE", "cpu")


@lru_cache
def get_model(model: Literal["base", "large"]) -> AlignScore:
    """Initialize a model.

    Args
        model: The type of the model to be loaded, i.e. "base", "large".
    """
    if models_path is None:
        raise ValueError(
            "Please set the ALIGN_SCORE_PATH environment variable "
            "to point to the AlignScore checkpoints folder. "
        )
    model_path_with_name = os.path.join(models_path, f"AlignScore-{model}.ckpt")
    if not os.path.isfile(model_path_with_name):
        raise RuntimeError(
            "Model not found. Please check the ALIGN_SCORE_PATH environment variable."
        )

    return AlignScore(
        model="roberta-base",
        batch_size=32,
        device=device,
        evaluation_mode="nli_sp",
    )


class AlignScoreRequest(BaseModel):
    """The request body for the AlignScore endpoints."""

    evidence: str
    claim: str


class AlignScoreResponse(BaseModel):
    """The response body for the AlignScore endpoints."""

    alignscore: float


@app.get("/healthcheck")
def healthcheck() -> JSONResponse:
    """Healthcheck endpoint."""
    if models_path is None:
        return JSONResponse(
            status_code=500,
            content={"error": "Please set the ALIGN_SCORE_PATH environment variable "},
        )

    base_model_found = os.path.isfile(os.path.join(models_path, "AlignScore-base.ckpt"))
    large_model_found = os.path.isfile(
        os.path.join(models_path, "AlignScore-large.ckpt")
    )

    if base_model_found or large_model_found:
        return JSONResponse(
            status_code=200,
            content={
                "base_model_found": base_model_found,
                "large_model_found": large_model_found,
            },
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "base_model_found": base_model_found,
                "large_model_found": large_model_found,
            },
        )


@app.get("/")
def hello_world() -> str:
    """Welcome message."""

    welcome_str = (
        "This is a development server to host AlignScore models.\n"
        "<br>Hit the /alignscore_base or alignscore_large endpoints with "
        "a POST request containing evidence and claim.\n"
        '<br>Example: curl -X POST -d \'{"evidence":"evidence","claim":"claim"}\''
        " -H 'Content-Type: application/json' http://localhost:5001/alignscore_base"
    )
    return welcome_str


def get_alignscore(model: AlignScore, evidence: str, claim: str) -> AlignScoreResponse:
    """Wrapper for AlignScore"""
    return AlignScoreResponse(
        alignscore=model.score(contexts=[evidence], claims=[claim])[0]
    )


@app.post("/alignscore_base")
def alignscore_base(request: AlignScoreRequest) -> AlignScoreResponse:
    """Get the AlignScore for a given evidence and claim using the base model."""
    model = get_model("base")
    return get_alignscore(model, request.evidence, request.claim)


@app.post("/alignscore_large")
def alignscore_large(request: AlignScoreRequest) -> AlignScoreResponse:
    """Get the AlignScore for a given evidence and claim using the large model."""
    model = get_model("large")
    return get_alignscore(model, request.evidence, request.claim)


cli_app = typer.Typer()


@cli_app.command()
def start(
    port: int = typer.Option(
        default=5000, help="The port that the server should listen on. "
    ),
    models: List[str] = typer.Option(
        default=["base"],
        help="The list of models to be loaded on startup",
    ),
    initialize_only: bool = typer.Option(
        default=False, help="Whether to run only the initialization for the models."
    ),
) -> None:
    """CLI app for AlignScore server."""
    # Preload the models
    for model in models:
        typer.echo(f"Pre-loading model {model}.")
        get_model(model)

    if initialize_only:
        print("Initialization successful.")
    else:
        uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    """Run the typer cli app"""
    cli_app()
