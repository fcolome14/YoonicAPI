FROM python:3.10-bullseye

WORKDIR /usr/src/app

COPY ../requeriments.txt ./
RUN pip install --no-cache-dir -r requeriments.txt

COPY ../app ./app

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]