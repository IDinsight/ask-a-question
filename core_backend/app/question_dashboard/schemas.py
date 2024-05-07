from typing import List

from pydantic import BaseModel


class QuestionDashBoard(BaseModel):
    six_months_questions: List[int]
    six_months_upvotes: List[int]
