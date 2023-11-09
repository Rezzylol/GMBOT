FROM python:3.11-alpine

WORKDIR /bot

RUN pip install --upgrade pip && \
	pip install --upgrade setuptools wheel

ADD ./app /bot/app
RUN pip install -r /bot/app/requirements.txt

ENV PYTHONUNBUFFERED 1
CMD ["python","./app/bot.py"]
