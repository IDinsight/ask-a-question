import os

# user 1
USER1_USERNAME = os.environ.get("USER1_USERNAME", "user1")
USER1_PASSWORD = os.environ.get("USER1_PASSWORD", "password")
USER1_RETRIEVAL_SECRET = os.environ.get("USER1_RETRIEVAL_SECRET", "user1-token")

# user 2
USER2_USERNAME = os.environ.get("USER2_USERNAME", "user2")
USER2_PASSWORD = os.environ.get("USER2_PASSWORD", "password")
USER2_RETRIEVAL_SECRET = os.environ.get("USER2_RETRIEVAL_SECRET", "user2-token")

ACCESS_TOKEN_EXPIRE_MINUTES = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.environ.get("JWT_SECRET", "jwt-secret")
