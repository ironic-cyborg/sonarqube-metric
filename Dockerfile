FROM python:3.10

WORKDIR /usr/src/app
COPY requirements.txt ./
COPY sonar-metrics.py ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python3", "sonar-metrics.py" ]
