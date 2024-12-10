FROM python:3.10-bullseye

WORKDIR /usr/src/app

COPY requeriments.txt ./

RUN pip install --no-cache-dir -r requeriments.txt

# Copy the wait-for-it.sh script into the image
# COPY wait-for-it.sh /usr/src/app/wait-for-it.sh

# RUN chmod +x /usr/src/app/wait-for-it.sh

COPY . .

EXPOSE 80

CMD ["bash", "-c", "./wait-for-it.sh ${DATABASE_HOSTNAME}:${DATABASE_PORT} -- alembic upgrade heads && uvicorn app.main:app --host 0.0.0.0 --port 80"]