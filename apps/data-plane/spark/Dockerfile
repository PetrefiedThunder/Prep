FROM bitnami/spark:3.5.1

USER root

COPY requirements.txt /opt/requirements.txt
RUN pip install --no-cache-dir -r /opt/requirements.txt

COPY . /opt/spark-jobs
WORKDIR /opt/spark-jobs

ENV PYTHONPATH=/opt/spark-jobs

ENTRYPOINT ["/opt/bitnami/scripts/spark/entrypoint.sh"]
CMD ["spark-submit", "--master", "local[*]", "spark_recon.py"]
