USER_CLIENT="philipp"
USER_SERVER="philipp"

PASSWORD_CLIENT="Heisenberg2199"
PASSWORD_SERVER="Heisenberg2199"

SERVER_IP="192.168.0.103"
CLIENT_IP="192.168.0.101"

CLIENT_INTERFACE="eth0"
SERVER_INTERFACE="eth0"

LSQUIC_PORT="4000"

check_device_ready() {
    local IP=$1
    local PASSWORD=$2
    local USER=$3
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$USER@$IP" "echo 'ready'" &> /dev/null
}

rebooting(){
    sshpass -p "$PASSWORD_SERVER" ssh -o StrictHostKeyChecking=no "$USER_SERVER@$SERVER_IP" "sudo reboot"
    sshpass -p "$PASSWORD_CLIENT" ssh -o StrictHostKeyChecking=no "$USER_CLIENT@$CLIENT_IP" "sudo reboot"
    while true; do
        if check_device_ready "$CLIENT_IP" "$PASSWORD_CLIENT" "$USER_CLIENT" && check_device_ready "$SERVER_IP" "$PASSWORD_SERVER" "$USER_SERVER"; then
            echo "Both devices are ready."
            break
        else
            echo "...waiting for devices to reboot and be ready..."
            sleep 5
        fi
        done
}

execute_ssh_command() {
    local user=$1
    local host=$2
    local password=$3
    local command=$4

    sshpass -p "$password" ssh -o StrictHostKeyChecking=no "$user@$host" "$command"
}

print_in_box() {
    local text="$1"
    local length=${#text}
    local border=$(printf '%*s' "$length" '' | tr ' ' '-')
    echo "+-${border}-+"    
    echo "| $text |"
    echo "+-${border}-+"
}

server_shutdown() {
    local port=$1
    SERVER_PIDS=$(execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "lsof -t -i:$port")
    if [ -n "$SERVER_PIDS" ]; then
        for PID in $SERVER_PIDS; do
            execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "sudo kill -9 $PID"
        done
    else
        echo "No processes found on port $port."
    fi
}

waiting_server_listening(){
    local port=$1
    echo "Waiting for server to start listening on port $port..."
    while true; do
        SERVER_PID=$(execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "lsof -i :$port -t")
        if [ -n "$SERVER_PID" ]; then
            echo "Server is listening on port $port with PID: $SERVER_PID"
            break
        else
            sleep 2
        fi
    done
}

kill_server(){
    local seconds=$1
    local port=$2
    sleep $seconds
    SERVER_PID=$(execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "lsof -i :$port -t")
    if [ -n "$SERVER_PID" ]; then
        execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "kill $SERVER_PID"
        echo "Server with PID $SERVER_PID has been killed."
    else
        echo "No server process found to kill on port $port."
    fi
}

simulate_normal(){
    local min_con=$1
    local max_con=$2
    local min_pause=$3
    local max_pause=$4
    local runtime=$5

    echo "Starting Aioquic base server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd /home/philipp/aioquic_base && source venv/bin/activate && python3 examples/http3_server.py --certificate cert.pem --private-key key.pem --host $SERVER_IP --port $LSQUIC_PORT' > server.log 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $LSQUIC_PORT

}

simulate_slowloris(){
echo "test"
}

simulate_flood(){
echo "test"
}

simulate_lsquic_http3(){
echo "test"
}


simulate_normal 1 3 4 10 30