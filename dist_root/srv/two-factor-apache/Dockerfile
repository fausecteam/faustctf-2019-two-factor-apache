FROM httpd:2.4

RUN echo 'deb http://ftp.debian.org/debian stretch-backports main' >> /etc/apt/sources.list.d/backports.list && \
    apt-get update && \
    apt-get -y install --no-install-recommends \
        python3 python3-pip python3-magic \
        libpam-oath oathtool \
        qrencode && \
    \
    pip3 install pamela flup && \
    \
    rm -rf /var/lib/apt/lists/* && \
    \
    touch /usr/local/sbin/spawn_apache_fcgi && \
    touch /etc/pam.d/2fapache && \
    mkdir /usr/local/apache2/sock_dir/ && \
    mkdir --mode=0700 /etc/liboath

CMD ["/usr/local/sbin/spawn_apache_fcgi"]
