import os

CONTENT_READONLY_PASSWORD = os.environ.get("CONTENT_READONLY_PASSWORD", "readonly")
ACCESS_TOKEN_EXPIRE_MINUTES = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.environ.get("JWT_SECRET", "jwt-secret")
QUESTION_ANSWER_SECRET = os.environ.get("QUESTION_ANSWER_SECRET", "update-me")
CONTENT_FULLACCESS_PASSWORD = os.environ.get(
    "CONTENT_FULLACCESS_PASSWORD", "fullaccess"
)
