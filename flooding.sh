concurrent_connections=$1
iterations=$2
url=$3 # e.g https://192.168.0.103:4000/index.html

trap "echo 'interput'; exit" SIGINT

for i in $(seq 1 $iterations)
do
   echo "Iteration $i"
   sudo seq 1 $concurrent_connections | xargs -n1 -P$concurrent_connections python3 examples/http3_client.py --zero-rtt --insecure $url
done

