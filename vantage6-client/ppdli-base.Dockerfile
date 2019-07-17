FROM python:3

COPY . /joey

RUN pip install /joey 
