#!/bin/bash

LOGFILE="/tmp/kernel_count.txt"
PSFILE="/tmp/ps.txt"
while true; do
  ps_output=$(ps aux)
  pids=( $(echo "$ps_output" | grep '[i]pykernel_launcher' | awk '{print $2 " " $9}' | sort -k2 | awk '{print $1}') )
  count=${#pids[@]}
  echo $count > "$LOGFILE"

  printf "%s\n" "${ps_output[@]}" > "$PSFILE"

  sleep 1
done