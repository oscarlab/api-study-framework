for f in `find $1 -executable`; do readelf -a $f &> /dev/null && echo $f; done
for f in `find $1 -name "lib*.so*" ! -type l`; do readelf -a $f &> /dev/null && echo $f; done
