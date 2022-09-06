FROM quay.io/condaforge/mambaforge:4.13.0-1

# if you forked pandas, you can pass in your own GitHub username to use your fork
# i.e. gh_username=myname
ARG gh_username=pandas-dev
ARG pandas_home="/home/pandas"

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Configure apt and install packages
RUN apt-get update \
    && apt-get -y install --no-install-recommends apt-utils dialog 2>&1 \
    #
    # Install tzdata and configure timezone (fix for tests which try to read from "/etc/localtime")
    && apt-get -y install tzdata \
    && ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    #
    # Verify git, process tools, lsb-release (common in install instructions for CLIs) installed
    && apt-get -y install git iproute2 procps lsb-release \
    #
    # cleanup
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Switch back to dialog for any ad-hoc use of apt-get
ENV DEBIAN_FRONTEND=dialog

# Clone pandas repo
RUN mkdir "$pandas_home" \
    && git clone "https://github.com/$gh_username/pandas.git" "$pandas_home" \
    && cd "$pandas_home" \
    && git remote add upstream "https://github.com/pandas-dev/pandas.git" \
    && git pull upstream main

# Set up environment
RUN mamba env create -f "$pandas_home/environment.yml"

# Build C extensions and pandas
SHELL ["mamba", "run", "-n", "pandas-dev", "/bin/bash", "-c"]
RUN cd "$pandas_home" \
    && export \
    && python setup.py build_ext -j 4 \
    && python -m pip install --no-build-isolation -e .
