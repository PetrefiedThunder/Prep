FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PREP_WEBHOOK_SECRET=changeme
EXPOSE 8787
CMD ["uvicorn","integrations.webhooks.server.main:app","--host","0.0.0.0","--port","8787"]
