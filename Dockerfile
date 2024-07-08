FROM python:3.11 AS requirements-stage

WORKDIR /tmp

RUN pip install poetry

# minimum for poetry install
COPY ./poetry.lock* ./pyproject.toml /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

####################################################################
#---
####################################################################

FROM python:3.11

ENV PYTHONUNBUFFERED=1

COPY --from=requirements-stage /tmp/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /tmp/requirements.txt ; pip install --no-cache-dir poetry

COPY ./ /usr/src/dataclay_restful

RUN pip install /usr/src/dataclay_restful

CMD ["uvicorn", "--factory", "dataclay_restful.web.application:get_app", "--host", "0.0.0.0", "--port", "80"]
