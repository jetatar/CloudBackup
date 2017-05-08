#!/bin/bash

export QUOTAS=/tmp/,quotas

cd /etc/beegfs/sbak.d

./beegfs-ctl --cfgFile=./beegfs-client.conf --getquota --uid --all > $QUOTAS

cat $QUOTAS

printf "\nQuotas data file [ $QUOTAS ]\n"
printf "Count = [ `wc -l $QUOTAS` ]\n"

