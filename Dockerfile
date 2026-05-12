FROM python:3.13-alpine
WORKDIR /app
RUN python -m pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["sh", "-c", "python start.py --env ${NODE_ENV:-prod}"]