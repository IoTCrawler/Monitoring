FROM python:3

RUN pip3 install requests flask python-dateutil

COPY static /static/
COPY html /html
COPY ngsi_ld /ngsi_ld
COPY other /other

ENV NGSI_ADDRESS 155.54.95.248:9090
ENV FD_HOST 0.0.0.0
ENV FD_PORT 8082
ENV FD_CALLBACK https://mobcom.ecs.hs-osnabrueck.de/faultdetection/callback

EXPOSE $FD_PORT

ADD config.ini configuration.py datasource_manager.py main.py /

CMD python3 main.py

