FROM ubuntu:latest

RUN apt-get update && apt-get install -y ubuntu-desktop

WORKDIR /lc-inspector

COPY . /lc-inspector

RUN pip install -r requirements.txt

RUN apt-get install -y x11-xserver-utils

ENV DISPLAY=:99

CMD ["python", "main.py"]