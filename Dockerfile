FROM ubuntu:20.04
#FROM python:3

#RUN apt-get update
#RUN apt-get install -y python3 python3-pip build-essential python3-dev octave octave-statistics r-base r-cran-randomfields
#RUN apt-get install -y --fix-missing python3 python3-pip octave octave-statistics r-base r-cran-randomfields
#RUN apt-get install -y octave octave-statistics r-base r-cran-randomfields
RUN apt-get update && DEBIAN_FRONTEND="noninteractive" apt-get install -y python3 python3-pip build-essential python3-dev octave octave-statistics r-base r-cran-randomfields
RUN mkdir /monitoring
WORKDIR /monitoring
COPY requirements.txt /monitoring/requirements.txt
RUN python3 -m pip install --upgrade pip && python3 -m pip install -r /monitoring/requirements.txt --use-deprecated=legacy-resolver
#RUN python3 -m pip install -r /monitoring/requirements.txt

RUN R -e "install.packages('geoR')"

# copy folders
COPY static /monitoring/static/
COPY html /monitoring/html
COPY ngsi_ld /monitoring/ngsi_ld
COPY other /monitoring/other
COPY datasets /monitoring/datasets
COPY fault_detection /monitoring/fault_detection
COPY fault_recovery /monitoring/fault_recovery

# copy files
COPY config.ini /monitoring/config.ini
COPY configuration.py /monitoring/configuration.py
COPY main.py /monitoring/main.py
COPY sensor.py /monitoring/sensor.py
COPY datasource_manager.py /monitoring/datasource_manager.py


ENV NGSI_ADDRESS http://155.54.95.248:9090
ENV FD_HOST 0.0.0.0
ENV FD_PORT 8082
ENV FD_CALLBACK https://mobcom.ecs.hs-osnabrueck.de/faultdetection/callback
ENV VS_CREATER_ADDRESS http://staging.vs-creator.iotcrawler.eu
#ENV RECOVERY_METHOD MCMC
ENV RECOVERY_METHOD BME

EXPOSE $FD_PORT

#ADD config.ini configuration.py datasource_manager.py main.py /

CMD python3 main.py
