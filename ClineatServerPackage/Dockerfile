# Build: docker build -t dockerfile .
# Run: Client/Server: docker run --network host -i -t dockerfile /bin/bash
# You can use the bash to run the server or client.
FROM ubuntu:18.04

# Install dependencies
RUN apt-get update && apt-get install -y python3.7 python3-pip

WORKDIR /usr/test

COPY . ./
RUN pip3 install --upgrade pip
