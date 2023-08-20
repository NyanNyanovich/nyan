#!/bin/bash

mkdir -p models
wget https://github.com/NyanNyanovich/nyan/releases/download/v0.3/nyan_models.tar.gz -O models/nyan_models.tar.gz
cd models && tar -xzvf nyan_models.tar.gz && rm nyan_models.tar.gz
