FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
WORKDIR /spike
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY gateway.py synthetic.py ./
USER 65534:65534
CMD ["uvicorn", "gateway:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
