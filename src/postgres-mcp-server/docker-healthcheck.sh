#!/bin/sh

<<<<<<< HEAD
if [ "$(lsof +c 0 -p 1 | grep -e "^awslabs\..*\s1\s.*\sunix\s.*socket$" | wc -l)" -ne "0" ]; then
  echo -n "$(lsof +c 0 -p 1 | grep -e "^awslabs\..*\s1\s.*\sunix\s.*socket$" | wc -l) awslabs.* streams found";
=======
if [ "$(lsof +c 0 -p 1 | grep -e grep -e "^awslabs\..*\s1\s.*\unix\s.*socket$" | wc -l)" -ne "0" ]; then
  echo -n "$(lsof +c 0 -p 1 | grep -e grep -e "^awslabs\..*\s1\s.*\unix\s.*socket$" | wc -l) awslabs.* streams found";
>>>>>>> 725dba2 (create the v1 of postgres-mcp-server which supports NL2SQL)
  exit 0;
else
  echo -n "Zero awslabs.* streams found";
  exit 1;
fi;

echo -n "Never should reach here";
exit 99;
