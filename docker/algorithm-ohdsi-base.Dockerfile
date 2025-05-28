ARG TAG=latest
ARG BASE=4.0
# ARG OHDSI_VERSION=0.3.2
FROM harbor2.vantage6.ai/infrastructure/algorithm-base:${BASE}

LABEL version=${TAG}
# LABEL ohdsi_version=${OHDSI_VERSION}
LABEL maintainer="F.C.Martin <f.martin@iknl.nl>"

# install dependencies for the ohdsi tools part of the wrapper
RUN apt-get update
RUN apt-get install -y build-essential libcurl4-gnutls-dev libxml2-dev \
                       libssl-dev dirmngr apt-transport-https ca-certificates \
                       software-properties-common gnupg2

# install R
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-key \
                            '95C0FAF38DB3CCAD0C080A7BDC78B2DDEABC47B7'
RUN add-apt-repository \
    'deb http://cloud.r-project.org/bin/linux/debian bullseye-cran40/'

RUN apt-get update
RUN apt-get install -y r-base

# install Java
RUN apt-get install -y openjdk-17-jre
RUN apt-get install -y openjdk-17-jdk

RUN R CMD javareconf

RUN Rscript -e "install.packages('DatabaseConnector')"
RUN Rscript -e "install.packages('drat')"
RUN Rscript -e "drat::addRepo('OHDSI'); install.packages('FeatureExtraction')"
RUN Rscript -e "install.packages('remotes')"
RUN Rscript -e "remotes::install_github('ohdsi/CirceR')"
RUN Rscript -e "remotes::install_github('OHDSI/CohortDiagnostics')"
RUN Rscript -e "remotes::install_github('OHDSI/CohortGenerator')"

# Install python OHDSI packages
RUN pip install ohdsi-database-connector
RUN pip install ohdsi-feature-extraction
RUN pip install ohdsi-circe
RUN pip install ohdsi-cohort-diagnostics
RUN pip install ohdsi-cohort-generator

RUN pip install psycopg2-binary

# Required for OHDSI R package to find the correct shared libs for Java.
# FIXME FM 5-9-2023: This is a bit to broad, it would be better to figure out
# a way to only set this for the OHDSI R packages.
ENV LD_LIBRARY_PATH=/usr/lib/jvm/java-17-openjdk-amd64/lib/server/

