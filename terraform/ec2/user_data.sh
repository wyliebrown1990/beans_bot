#!/bin/bash

## source:
## https://aws.amazon.com/premiumsupport/knowledge-center/ec2-linux-log-user-data/
exec > >( tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console ) 2>&1
## what is this magic? it works

mkdir /app
chown ec2-user /app

## 2.
## Install CloudWatch Agent
yum install amazon-cloudwatch-agent -y

## 3.
## Install psql
yum install postgresql -y

## 4.
## Install Docker-compose
sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose

sudo chmod +x /usr/local/bin/docker-compose

docker-compose version