import os

# user 1
USER1_USERNAME = os.environ.get("USER1_USERNAME", "user1")
USER1_PASSWORD = os.environ.get("USER1_PASSWORD", "fullaccess")
USER1_RETRIEVAL_KEY = os.environ.get("USER1_RETRIEVAL_KEY", "user1-key")

# user 2
USER2_USERNAME = os.environ.get("USER2_USERNAME", "user2")
USER2_PASSWORD = os.environ.get("USER2_PASSWORD", "fullaccess")
USER2_RETRIEVAL_KEY = os.environ.get("USER2_RETRIEVAL_KEY", "user2-key")

ACCESS_TOKEN_EXPIRE_MINUTES = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.environ.get("JWT_SECRET", "jwt-secret")
