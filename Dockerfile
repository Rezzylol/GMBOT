FROM python:3.11-alpine

WORKDIR /bot

ADD ./app /bot/app
RUN pip install --upgrade pip && \
	pip install --upgrade setuptools wheel && \
	pip install -r /bot/app/requirements.txt

ENV PYTHONUNBUFFERED 1
CMD ["python","./app/bot.py"]
