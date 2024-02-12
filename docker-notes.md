
Running anki in docker:

- on the host run `xhost +local:docker` before starting the docker container to solve `Could not connect to display :0`
- built the image with the AnkiConnect addon in the addons21 folder
  - configured AnkiConnect to accept connections on 0.0.0.0 before copying
  - ran the docker image with `-p 8765:8765` to make the AnkiConnect port available

