FROM python:3.11-bookworm

ARG LIBOQS_VERSION=0.14.0

ENV OQS_INSTALL_PATH=/usr/local \
    LD_LIBRARY_PATH=/usr/local/lib \
    PYOQS_VERSION=${LIBOQS_VERSION}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        cmake \
        git \
        libssl-dev \
        ninja-build \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth=1 --branch "${LIBOQS_VERSION}" https://github.com/open-quantum-safe/liboqs /tmp/liboqs \
    && cmake -S /tmp/liboqs -B /tmp/liboqs/build -G Ninja \
        -DBUILD_SHARED_LIBS=ON \
        -DOQS_BUILD_ONLY_LIB=ON \
        -DCMAKE_INSTALL_PREFIX=/usr/local \
    && cmake --build /tmp/liboqs/build --parallel \
    && cmake --install /tmp/liboqs/build \
    && ldconfig \
    && rm -rf /tmp/liboqs

COPY requirements.txt /tmp/pqc-requirements.txt

RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r /tmp/pqc-requirements.txt \
    && python -c "import oqs; print('liboqs', oqs.oqs_version()); assert 'ML-DSA-87' in oqs.get_enabled_sig_mechanisms()"
