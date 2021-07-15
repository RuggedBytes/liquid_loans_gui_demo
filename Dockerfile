FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Berlin
RUN apt-get update && apt-get upgrade -qy

COPY ./ /app

RUN apt-get install -yq build-essential libtool autotools-dev autoconf pkg-config libssl-dev libboost-all-dev
RUN apt-get install -yq libqt5gui5 libqt5core5a libqt5dbus5 qttools5-dev qttools5-dev-tools libprotobuf-dev protobuf-compiler imagemagick librsvg2-bin
RUN apt-get install -yq libqrencode-dev autoconf openssl libssl-dev libevent-dev libminiupnpc-dev git bsdmainutils xdg-utils
RUN apt-get install -yq python3-pip
RUN apt-get install -yq libdb++-dev
RUN apt-get install -yq epiphany-browser
RUN xdg-settings set default-web-browser org.gnome.Epiphany.desktop

RUN cd /root && git clone https://github.com/ElementsProject/elements.git
WORKDIR /root/elements 
RUN git checkout elements-0.18.1.12 && ./autogen.sh && ./configure --with-incompatible-bdb --without-gui --without-miniupnpc --disable-tests --disable-bench && make && make install
RUN mkdir ~/elementsdir1 && mkdir ~/elementsdir2
RUN sed 's/validatepegin=1/validatepegin=0/g;s/elementsregtest/liquidregtest/g' ~/elements/contrib/assets_tutorial/elements1.conf > ~/elementsdir1/elements.conf
RUN echo 'chain=liquidregtest' > ~/elementsdir2/elements.conf
RUN sed 's/validatepegin=1/validatepegin=0/g;s/elementsregtest/liquidregtest/g' ~/elements/contrib/assets_tutorial/elements2.conf >> ~/elementsdir2/elements.conf

RUN echo export LC_ALL=C.UTF-8 >> ~/.bashrc
RUN echo export LANG=C.UTF-8 >> ~/.bashrc

WORKDIR /root

RUN cd /root && git clone https://github.com/ElementsProject/secp256k1-zkp
WORKDIR /root/secp256k1-zkp
RUN ./autogen.sh && ./configure --prefix=/usr --enable-experimental --enable-module-generator --enable-module-rangeproof --enable-module-surjectionproof --enable-module-ecdh --enable-module-recovery && make && make install

WORKDIR /root
RUN pip3 install pip --upgrade
RUN pip3 install python-bitcointx
RUN pip3 install python-elementstx
RUN pip3 install ecdsa
RUN pip3 install attrs
RUN pip3 install click
RUN pip3 install isort
RUN pip3 install black
RUN pip3 install colour
RUN adduser --quiet --disabled-password qtuser
RUN pip3 install pyqt5
RUN pip3 install pyqt5-tools
RUN pip3 install pyinstaller

ADD ./prepare.sh ./cli/devel/split.py ./entry.sh ./issues.py /root/
RUN ./prepare.sh

# cleanup
RUN apt-get --auto-remove remove -yqq --purge manpages \
 && apt-get clean \
 && apt-get autoclean \
 && rm -rf /usr/share/doc* /usr/share/man /usr/share/postgresql/*/man /var/lib/apt/lists/* /var/cache/* /tmp/* /root/.cache /*.deb /root/.cargo

ENTRYPOINT ["/root/entry.sh"]
