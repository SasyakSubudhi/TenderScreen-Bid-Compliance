FROM python:3.12-slim
WORKDIR /service
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 --retries=5 -r requirements.txt
COPY app app
COPY corpus corpus
COPY prompts prompts
COPY web web
COPY scripts scripts
COPY tests tests
COPY eval eval
COPY examples examples
COPY docs docs
RUN mkdir -p /service/data /service/evidence && useradd --uid 10001 --create-home runner && chown -R runner:runner /service
USER runner
CMD ["python", "-m", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
