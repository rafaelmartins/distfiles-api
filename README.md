# distfiles-api
A simple HTTP endpoint to upload distfiles from Travis CI.


## Client usage:

    $ curl ${TOKEN}@localhost/ \
          -F 'file=@blogc-0.13.0.tar.gz' \
          -F 'project=blogc' \
          -F 'version=0.13.0' \
          -F "sha512=$(sha512sum blogc-0.13.0.tar.gz)" \
          -F "extract=false"
