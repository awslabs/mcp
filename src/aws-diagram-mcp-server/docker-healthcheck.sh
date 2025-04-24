#!/bin/sh

if [ "$(lsof +c 0 -p 1 +E | grep -e "^awslabs\..*\s1\s.*\s.*\sunix\s.*type=STREAM" | wc -l)" -ne "0" ]; then
  echo -n "$(lsof +c 0 -p 1 +E | grep -e "^awslabs\..*\s1\s.*\s.*\sunix\s.*type=STREAM" | wc -l) awslabs.* streams found";
  exit 0;
else
  echo -n "Zero awslabs.* streams found";
  exit 1;
fi;

echo -n "Never should reach here";
exit 99;
