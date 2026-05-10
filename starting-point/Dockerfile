FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com pip --upgrade

COPY pyproject.toml .
COPY src/ src/
COPY static/ static/

RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com .

EXPOSE 8000

CMD ["uvicorn", "starting_point.main:app", "--host", "0.0.0.0", "--port", "8000"]
