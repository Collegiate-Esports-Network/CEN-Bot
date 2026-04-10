FROM python:3.14-slim
WORKDIR /app
RUN python -m pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["sh", "-c", "python start.py --env ${NODE_ENV:-prod}"]