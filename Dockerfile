FROM python:3.13.0
ADD . /code
COPY start.sh .
COPY main.py /code
WORKDIR /code
RUN pip install -r requirements.txt
ENV database="None"
ENV api="None"
ENTRYPOINT /bin/bash /start.sh $database $api
