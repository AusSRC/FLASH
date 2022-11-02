FROM ubuntu:latest
ARG DEBIAN_FRONTEND=noninteractive

RUN apt update &&apt install -y \
	curl \
	vim \
	sudo \
	python3 python3-scipy python3-pip \
	python3-matplotlib python3-progressbar \
	python3-ipython \
	libblas-dev \
	liblapack-dev \
	libatlas3-base libatlas-base-dev \
	cmake build-essential git gfortran 

RUN pip3 install astropy corner

RUN adduser --disabled-password --gecos "" flash
ENV HOME="/home/flash"

COPY flash.tar.gz $HOME
RUN mkdir /data
VOLUME /data

WORKDIR $HOME
RUN tar -zxvf flash.tar.gz
RUN chown -R flash:flash $HOME
USER flash
WORKDIR $HOME/PyMultiNest/MultiNest/build/
RUN rm -R CMake* src
RUN cmake ..
RUN make

WORKDIR $HOME


