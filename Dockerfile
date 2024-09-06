FROM python:3.10.8
WORKDIR /home/pandas

# Install build essentials and dependencies
RUN apt-get update && apt-get -y upgrade && \
    apt-get install -y build-essential bash-completion libhdf5-dev libgles2-mesa-dev

# Install Python dependencies
RUN python -m pip install --upgrade pip
COPY requirements-dev.txt /tmp
RUN python -m pip install -r /tmp/requirements-dev.txt

# Configure Git
RUN git config --global --add safe.directory /home/pandas

ENV SHELL "/bin/bash"
CMD ["/bin/bash"]
