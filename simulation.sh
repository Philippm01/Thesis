USER_CLIENT="philipp"
USER_SERVER="philipp"

PASSWORD_CLIENT="Heisenberg2199"
PASSWORD_SERVER="Heisenberg2199"

SERVER_IP="192.168.0.103"
CLIENT_IP="192.168.0.101"

CLIENT_INTERFACE="eth0"
SERVER_INTERFACE="eth0"

AIOQUIC_PORT="4000"
LSQUIC_PORT=""

SERVER_AIQOUIC_PATH="/home/philipp/aioquic_base"

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
    (sleep $seconds
    SERVER_PID=$(execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "lsof -i :$port -t")
    if [ -n "$SERVER_PID" ]; then
        execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "kill $SERVER_PID"
        echo "Server with PID $SERVER_PID has been killed."
    else
        echo "No server process found to kill on port $port."
    fi) &
}

simulate_flood(){
    local min_con=$1
    local max_con=$2
    local runtime=$3
    local url=https://$SERVER_IP:$AIOQUIC_PORT/index.html
    local SECRETS_FILE="secrets.txt"
    local capture_file="simulation_capture.pcap"
    local decrypted_file="packet_capture/flood_con:"$min_con"-"$max_con"_time:"$runtime"_decrypted.pcap"

    #-----------------------------------------------Server Setup and Capturing---------------------------------------------
    echo "Starting Aioquic base server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd /home/philipp/aioquic_base && source venv/bin/activate && python3 examples/http3_server.py --certificate cert.pem --private-key key.pem --host $SERVER_IP --port $AIOQUIC_PORT -l aioquiclog ' > server.log 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $AIOQUIC_PORT
    echo "Capturing traffic on the server"
    CAPTURE_COMMAND="nohup sudo tshark -i $SERVER_INTERFACE -f 'port $AIOQUIC_PORT' -a duration:$runtime -w /tmp/$capture_file > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$CAPTURE_COMMAND"

    #-----------------------------------------------Client traffic generation----------------------------------------------
    echo "Starting Flooding Client"
    CLIENT_COMMAND="nohup bash -c 'cd /home/philipp/aioquic_flood && source venv/bin/activate && ./flood.sh $min_con $max_con $runtime $url' > client.log 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$CLIENT_COMMAND"
    sleep $runtime

    #--------------------------------------------------------Analysis-------------------------------------------------------
    echo "Decryption of traffic"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:/home/philipp/aioquic_base/aioquiclog" ./aioquiclog_temp 
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm /home/philipp/aioquic_base/aioquiclog"
    cat aioquiclog_temp >> "$SECRETS_FILE"
    rm aioquiclog_temp
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "sudo chown $USER_SERVER:$USER_SERVER /tmp/$capture_file"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:/tmp/$capture_file" ./packet_capture/
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm /tmp/$capture_file"
    tshark -r ./packet_capture/$capture_file -o tls.keylog_file:$SECRETS_FILE -w $decrypted_file
    #tshark -r $decrypted_file -o tls.keylog_file:$SECRETS_FILE -V > packet_capture/decrypted_output.txt
    rm $SECRETS_FILE
    rm ./packet_capture/$capture_file
}   

simulate_slowloris(){
echo "test"
}

simulate_normal(){
echo "test"
}

simulate_lsquic_http3(){
echo "test"
}


simulate_flood 10 30 30