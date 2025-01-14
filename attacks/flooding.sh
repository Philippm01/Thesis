lower_bound_connections=$1
upper_bound_connections=$2
runtime_seconds=$3
url=$4 # e.g https://192.168.0.103:4000/index.html

trap "echo 'interput'; exit" SIGINT

end_time=$((SECONDS + runtime_seconds))

while [ $SECONDS -lt $end_time ]
do
   echo "Running..."
   concurrent_connections=$((RANDOM % (upper_bound_connections - lower_bound_connections + 1) + lower_bound_connections))
   sudo seq 1 $concurrent_connections | xargs -n1 -P$concurrent_connections python3 examples/http3_client.py --zero-rtt --insecure $url
done

