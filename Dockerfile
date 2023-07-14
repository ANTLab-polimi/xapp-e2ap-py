#------------------------------------
ARG SCHEMA_PATH=schemas
ARG XAPP_DIR=python_xapp
ARG DBAAS_SERVICE_HOST=10.0.2.12
ARG DBAAS_SERVICE_PORT="6379"

#==================================================================================
FROM ubuntu:20.04
#FROM python:3.8-alpine

# copy local repo
ARG XAPP_DIR="/python_xapp"
ARG STAGE_DIR="/tmp"


# to override repo base, pass in repo argument when running docker build:
# docker build --build-arg REPOBASE=http://abc.def.org . ....
ARG SCHEMA_FILE
ARG SCHEMA_PATH
ARG MDC_VER=0.0.4-1
ARG RMR_VER=4.0.5
ARG RNIB_VER=1.0.0
ARG E2AP_VERSION=1.1.0
ARG DEBIAN_FRONTEND=noninteractive

ENV RMR_RTG_SVC="9999" \
  RMR_SEED_RT="/python_xapp/routes.txt" \
  LD_LIBRARY_PATH="/usr/local/lib:/usr/local/libexec" \
  VERBOSE=0 \
  CONFIG_FILE=/opt/ric/config/config-file.json \
  DBAAS_SERVICE_HOST=${DBAAS_SERVICE_HOST} \
  DBAAS_SERVICE_PORT=${DBAAS_SERVICE_PORT}

# install git and build essential
#RUN apk add --no-cache --update alpine-sdk wget dpkg cmake openrc openssh
RUN apt-get update && apt-get install -y git build-essential gfortran libopenblas-dev python3 python3-pip cmake openssh-server

# Install py-plt
WORKDIR ${STAGE_DIR}
RUN git clone https://github.com/o-ran-sc/ric-plt-xapp-frame-py.git
WORKDIR ric-plt-xapp-frame-py
RUN git checkout e-release
RUN python3 -m pip install .

# install protobuf
RUN python3 -m pip install protobuf

# install cvxpy
RUN python3 -m pip install cvxpy

# install rmr
WORKDIR ${STAGE_DIR}
RUN  git clone --branch e-release https://gerrit.oran-osc.org/r/ric-plt/lib/rmr \
     && cd rmr \
     && mkdir .build; cd .build \
     && echo "<<<installing rmr devel headers>>>" \
     && cmake .. -DDEV_PKG=1; make install \
     && echo "<<< installing rmr .so>>>" \
     && cmake .. -DPACK_EXTERNALS=1; make install \
     && echo "cleanup" \
     && cd ../.. \
     && rm -rf rmr

# install e2ap lib
WORKDIR ${STAGE_DIR}
RUN git clone --branch ${E2AP_VERSION} https://github.com/o-ran-sc/ric-plt-libe2ap.git \
  && cd ric-plt-libe2ap \
  && cmake . \
  && make \
  && make install

COPY . ${XAPP_DIR}
WORKDIR ${XAPP_DIR}

# cleanup
RUN rm -rf ${STAGE_DIR}/*

# ssh server
RUN mkdir /var/run/sshd
RUN echo 'root:pass' | chpasswd
RUN mkdir -p /root/.ssh \
    && chmod 0700 /root/.ssh \
    && echo 'root:pass' | chpasswd \
    && mkdir -p /run/openrc \
    && touch /run/openrc/softlevel

RUN sed 's@session\s*required\s*pam_loginuid.so@session optional \
    pam_loginuid.so@g' -i /etc/pam.d/sshd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' \
    /etc/ssh/sshd_config

#expose port 22
EXPOSE 22

#Commands to be executed by default
CMD ["/usr/sbin/sshd","-D"]