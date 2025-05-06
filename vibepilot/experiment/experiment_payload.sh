#!/bin/bash
sudo yum install amazon-efs-utils -y

mkdir -p /data
mount -t efs fs-0a339851322a7e6db /data

export DIR=/data/vibepilot/test_experiment

mkdir -p $DIR

FILE=$DIR/test_file.txt
touch "$FILE"

n=$(wc -l < "$FILE")

echo "$n" >> "$FILE"

echo "Number of lines in the file: $n"
echo "Contents of the file:"
cat "$FILE"

if [ "$n" -lt 3 ]; then
    echo "Less than 3 lines in the file, shutting down..."
    shutdown now
fi

