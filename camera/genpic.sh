#!/bin/bash
while [ true ]; do
    raspistill -vf -hf -o /var/www/frame.jpg
    sleep 1
done
