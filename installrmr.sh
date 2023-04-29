 #!/bin/sh
 git clone --branch 1.13.1 https://gerrit.oran-osc.org/r/ric-plt/lib/rmr \
     && cd rmr \
     && mkdir .build; cd .build \
     && echo "<<<installing rmr devel headers>>>" 
     && cmake .. -DDEV_PKG=1; make install \
     && echo "<<< installing rmr .so>>>" \
     && cmake .. -DPACK_EXTERNALS=1; sudo make install \
     && echo "cleanup" \
     && cd ../.. \
     && rm -rf rmr
