#!/bin/bash
while [ true ]; do
    raspistill -vf -hf -o ./frame.jpg
    sleep 1
done
