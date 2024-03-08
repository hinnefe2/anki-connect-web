# anki-connect-web
Run Anki + AnkiConnect in a VM and expose it to the web through a Flask app

## VM Setup

1. spin up a cloud instance
    - make sure to enable a virtual display
2. follow the linux installation instructions for Anki: https://docs.ankiweb.net/platform/linux/installing.html
2. install necessary packages. on a gcp debian instance:
    - wget
    - zstd
    - xdg-utils
    - netcat
    - qt6-base-dev
    - libnss3
    - libasound2
3. install vnc server
    - sudo apt install tightvncserver
    - export QT_QPA_PLATFORM=offscreen 
    - open up port 5901 on the instance firewall
4. install AnkiConnect
    - https://foosoft.net/projects/anki-connect/
5. install python + pip + flask
    - open up whatever port flask is running on
6. pip install aqt
7. import the `anki.collection.Collection` object
    - call `Collection.sync_login(..)` to get a `SyncAuth`
       - the endpoint is something like `server8.ankiweb.net` or similar
    - call `Collection.full_upload_or_download(..., upload=False)`
