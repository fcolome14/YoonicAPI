FROM python:3.10-bullseye

WORKDIR /usr/src/app

COPY requeriments.txt ./

RUN pip install --no-cache-dir -r requeriments.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]