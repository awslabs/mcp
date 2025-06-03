#!/bin/sh

if [ "$(lsof +c 0 -p 1 | grep -e "^awslabs\..*\s1\s.*\sunix\s.*\stype=STREAM (CONNECTED)$" | wc -l)" -ne "0" ]; then
  echo -n "$(lsof +c 0 -p 1 | grep -e "^awslabs\..*\s1\s.*\sunix\s.*\stype=STREAM (CONNECTED)$" | wc -l) awslabs.* streams found";
  exit 0;
else
  echo -n "Zero awslabs.* streams found";
  exit 1;
fi;
