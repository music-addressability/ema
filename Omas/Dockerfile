FROM ubuntu

RUN apt-get update &&\
    apt-get install -y build-essential python-dev python-setuptools python-pip \
    libboost-python-dev libboost-thread-dev wget cmake uuid-dev

RUN mkdir /code
WORKDIR /code

RUN wget https://github.com/DDMAL/libmei/archive/3.1.0.tar.gz &&\
    tar xvfz 3.1.0.tar.gz &&\
    rm 3.1.0.tar.gz &&\
    mkdir libmei-3.1.0/build

WORKDIR libmei-3.1.0
RUN sed -zi 's/if (CMAKE_COMPILER_IS_GNUCXX)\n    add_definitions( -Werror )\nendif (CMAKE_COMPILER_IS_GNUCXX)//' CMakeLists.txt

WORKDIR build
RUN cmake .. && make && make install

WORKDIR /code/libmei-3.1.0/python
RUN sed -zi 's/python27-mt/python27/' setup.py &&\
    sed -zi 's/boost_python-mt-py/boost_python-py/' setup.py

RUN python setup.py build && python setup.py install

WORKDIR /code
RUN wget https://github.com/umd-mith/ema/archive/v1.0.3.tar.gz &&\
    tar xvfz v1.0.3.tar.gz &&\
    rm v1.0.3.tar.gz

WORKDIR ema-1.0.3/Omas
RUN pip install -r requirements.txt

ENV OMAS_HOST 0.0.0.0
ENV OMAS_PORT 5000

ENTRYPOINT ["python", "api.py"]
