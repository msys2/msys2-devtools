FROM ubuntu:20.04 AS build
WORKDIR /tmp

RUN \
    apt update && \
    env DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends \
        asciidoc \
        ca-certificates \
        curl \
        docbook-xml \
        docbook-xsl \
        g++ \
        gnupg \
        libarchive-dev \
        libcurl4-openssl-dev \
        libgpgme-dev \
        libssl-dev \
        m4 \
        meson \
        patchutils \
        pkg-config \
        python3-setuptools \
        xsltproc \
    && \
    rm -Rf /var/{cache/apt,lib/apt/lists,log/{alternatives.log,apt,dpkg.log}} && \
true

RUN \
    gpg --update-trustdb && \
    gpg --keyserver hkps://keyserver.ubuntu.com --recv-keys 6645B0A8C7005E78DB1D7864F99FFE0FEAE999BD && \
    echo '5\ny\n' | gpg --command-fd 0 --no-tty --edit-key 6645B0A8C7005E78DB1D7864F99FFE0FEAE999BD trust && \
    gpg --keyserver hkps://keyserver.ubuntu.com --recv-keys B8151B117037781095514CA7BBDFFC92306B1121 && \
    echo '5\ny\n' | gpg --command-fd 0 --no-tty --edit-key B8151B117037781095514CA7BBDFFC92306B1121 trust && \
    gpg --update-trustdb && \
true

RUN \
    curl -sLO https://sources.archlinux.org/other/pacman/pacman-5.2.2.tar.gz && \
    curl -sLO https://sources.archlinux.org/other/pacman/pacman-5.2.2.tar.gz.sig && \
    gpg --verify --status-fd 1 pacman-5.2.2.tar.gz.sig pacman-5.2.2.tar.gz | grep -qE '^\[GNUPG:\] TRUST_(FULLY|ULTIMATE).*$' && \
    tar -xzf pacman-5.2.2.tar.gz && \
    rm pacman-5.2.2.tar.gz pacman-5.2.2.tar.gz.sig && \
true

COPY *.patch ./
RUN \
    cd pacman-5.2.2/ && \
    for patch in ../*.patch; do \
        patch -p1 -i "${patch}"; \
    done && \
    rm ../*.patch && \
true

RUN \
    { \
        meson setup build/ pacman-5.2.2/ \
            --buildtype=release \
            --prefix=/usr/local \
            --libdir=lib \
            -Duse-git-version=false \
        || cat build/meson-logs/meson-log.txt >&2; \
    } && \
    ninja -C build/ && \
    DESTDIR=/tmp/install meson install -C build/ && \
true

FROM ubuntu:20.04
RUN \
    apt update && \
    env DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends \
        gnupg \
        libarchive13 \
        libarchive-tools \
        libcurl4 \
        libgpgme11 \
        libssl1.1 \
    && \
    rm -Rf /var/{cache/apt,lib/apt/lists,log/{alternatives.log,apt,dpkg.log}} && \
true
COPY --from=build /tmp/install /
RUN ldconfig
