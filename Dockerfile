FROM faridh/python3-flyway

ADD requirements.txt /src/requirements.txt
RUN cd /src && pip install -r requirements.txt

ADD ./sql /opt/flyway-3.2.1/sql/
ADD . /src/
WORKDIR /src/
