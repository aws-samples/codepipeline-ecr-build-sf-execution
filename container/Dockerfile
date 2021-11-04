# Build an image that can do training and inference in SageMaker
# This is a Python 2 image that uses the nginx, gunicorn, flask stack
# for serving inferences in a stable way.

FROM public.ecr.aws/lts/ubuntu:20.04
RUN apt update
RUN apt install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt install -y python3.7

# install pip 
RUN apt install -y python3-pip

RUN apt-get install -y --no-install-recommends nginx ca-certificates
RUN rm -rf /var/lib/apt/lists/*

RUN python3.7 -m pip install langid
RUN python3.7 -m pip install langdetect
RUN python3.7 -m pip install emoji
RUN python3.7 -m pip install nltk==3.2.5
RUN python3.7 -m pip install pandas==1.1.5
RUN python3.7 -m pip install numpy==1.19.5
RUN python3.7 -m pip install torch
RUN python3.7 -m pip install transformers
RUN python3.7 -m pip install flask
RUN python3.7 -m pip install gevent==1.5.0
RUN python3.7 -m pip install gunicorn
RUN python3.7 -m pip install sklearn
RUN python3.7 -m pip install gensim
RUN python3.7 -m pip install xlrd
RUN python3.7 -m pip install openpyxl

# Set some environment variables. PYTHONUNBUFFERED keeps Python from buffering our standard
# output stream, which means that logs can be delivered to the user quickly. PYTHONDONTWRITEBYTECODE
# keeps Python from writing the .pyc files which are unnecessary in this case. We also update
# PATH so that the train and serve programs are found when the container is invoked.

ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PATH="/opt/program:${PATH}"

# Set up the program in the image
COPY decision_trees /opt/program
WORKDIR /opt/program

RUN chmod +x /opt/program/train
RUN chmod +x /opt/program/serve
