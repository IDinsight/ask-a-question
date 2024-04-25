# from fastapi import APIRouter, Depends
#
# from ..auth.dependencies import auth_bearer_token
#
# router = APIRouter(dependencies=[Depends(auth_bearer_token)])
#
#
# @router.post("/classify", response_model=ClassificationResponse)
# async def classify_text(request: ClassificationRequest):
#     raw_text = request.text_to_match
#     classifier = classifiers[CLASSIFIER_NAME]
#     prediction, metadata = classifier.predict(raw_text, return_metadata=True)
#
#     save_classification_to_db(prediction, metadata)
#
#     return ClassificationResponse(prediction=prediction, metadata={})
