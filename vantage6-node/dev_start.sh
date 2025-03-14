#!/bin/bash

# start a node for each config file the provided directory

config_dir=$1
if [ -z "$config_dir" ]; then
    echo "Provide a configuration directory as argument"
    exit 1
fi

# python_pids=()
for config in $config_dir/*.yaml; do
    echo "Starting node with config: $config"
    python /vantage6/vantage6-node/vantage6/dev_start.py $config &
    # python_pids+=($!)
done

# TODO we need to decide what we want to do here. Now I put sleep infinity to keep the
# node container running. This has the advantage that once the node crashes, the
# container will keep running and therefore, the error should be most visible in the
# logs. There is also (commented-out) code to check if a Python process has exited
# and if so, exit the script with the exit code of the Python process. This will lead
# to continuous restarts of the node - good for production but also nice for development?
sleep infinity

# Note: after deciding what to do (see TODO above), we need either to remove this code
# or to improve it (it's not really readable as it is now)
# # Function to check if a PID is from a Python process
# is_python_process() {
#     local pid=$1
#     # Check if process exists and is a Python process
#     if ps -p $pid -o comm= 2>/dev/null | grep -q "python"; then
#         return 0
#     else
#         return 1
#     fi
# }

# # Wait for any process to exit
# while true; do
#     # Wait for next process to exit and get its PID
#     wait -n
#     exit_code=$?

#     # Find which process exited
#     for pid in "${python_pids[@]}"; do
#         if ! kill -0 $pid 2>/dev/null; then
#             # If it was a Python process that exited, exit the script
#             if is_python_process $pid; then
#                 echo "Python process $pid exited with code $exit_code"
#                 exit $exit_code
#             fi
#         fi
#     done
# done
