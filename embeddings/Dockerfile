FROM python:3.11

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./main.py /app
#COPY ./model /app/model  

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]