#!/bin/bash

e2ap_version=1.1.0
wget -nv --content-disposition https://packagecloud.io/o-ran-sc/release/packages/debian/stretch/riclibe2ap_${e2ap_version}_amd64.deb/download.deb
wget -nv --content-disposition https://packagecloud.io/o-ran-sc/release/packages/debian/stretch/riclibe2ap-dev_${e2ap_version}_amd64.deb/download.deb

dpkg -i riclibe2ap_${e2ap_version}_amd64.deb
dpkg -i riclibe2ap-dev_${e2ap_version}_amd64.deb
