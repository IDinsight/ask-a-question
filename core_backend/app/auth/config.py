import os

USER1_USERNAME = os.environ.get("USER1_USERNAME", "user_one")
USER1_PASSWORD = os.environ.get("USER1_PASSWORD", "fullaccess")
USER2_USERNAME = os.environ.get("USER2_USERNAME", "user_two")
USER2_PASSWORD = os.environ.get("USER2_PASSWORD", "fullaccess")

QUESTION_ANSWER_SECRET = os.environ.get("QUESTION_ANSWER_SECRET", "update-me")

ACCESS_TOKEN_EXPIRE_MINUTES = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.environ.get("JWT_SECRET", "jwt-secret")
