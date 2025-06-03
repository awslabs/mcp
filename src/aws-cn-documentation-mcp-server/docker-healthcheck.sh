#!/bin/sh

if [ "$(lsof +c 0 -p 1 | grep -v grep | grep -e "^awslabs\..*\s1\s.*\unix\s.*socket$" | wc -l)" -ne "0" ]; then
  echo -n "$(lsof +c 0 -p 1 | grep -v grep | grep -e "^awslabs\..*\s1\s.*\unix\s.*socket$" | wc -l) awslabs.* streams found";
  exit 0;
else
  echo -n "Zero awslabs.* streams found";
  exit 1;
fi;
