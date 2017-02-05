FROM python:3.5-alpine

RUN apk --no-cache add bash && \
    addgroup user && \
    adduser -s /bin/bash -D -G user user

WORKDIR /app

COPY docker_build ./docker_build

RUN  cp docker_build/code/* ./ -r && \
     cd docker_build && \
     pip install -r requirements.txt && \
     chown -R user:user /app

USER user

CMD ["python", "run.py"]
