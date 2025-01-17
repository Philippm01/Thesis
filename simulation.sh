USER_CLIENT="philipp"
USER_SERVER="philipp"

PASSWORD_CLIENT="Heisenberg2199"
PASSWORD_SERVER="Heisenberg2199"

CLIENT_IP="192.168.0.101"
SERVER_IP="192.168.0.103"

CLIENT_INTERFACE="eth0"
SERVER_INTERFACE="eth0"

AIOQUIC_PORT="4000"
LSQUIC_PORT="4001"

SERVER_DIR="/home/philipp"
CLIENT_DIR="/home/philipp"

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
    local url_a=https://$SERVER_IP:$AIOQUIC_PORT/index.html
    local url_l=https://$SERVER_IP:$LSQUIC_PORT/index.html
    local SECRETS_FILE="secrets.txt"
    local capture_file="simulation_capture.pcap"
    local result_file="packet_capture/flood_con:"$min_con"-"$max_con"_time:"$runtime".pcap"

    #-----------------------------------------------Server Setup and Capturing---------------------------------------------
    echo "Starting Aioquicserver on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && python3 examples/http3_server.py --certificate cert.pem --private-key key.pem --host $SERVER_IP --port $AIOQUIC_PORT -l aioquiclog ' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $AIOQUIC_PORT

    echo "Starting LSQUIC server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/lsquic/bin && ./http_server -c $SERVER_IP,fullchain.pem,privkey.pem -s 0.0.0.0:$LSQUIC_PORT -r /home/philipp/www/ -G /home/philipp/lsquic/bin/keys' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $LSQUIC_PORT

    echo "Capturing traffic on Port $LSQUIC_PORT and $AIQOUIC_PORT"
    CAPTURE_COMMAND="nohup sudo tshark -i $SERVER_INTERFACE -f 'port $AIOQUIC_PORT or port $LSQUIC_PORT' -a duration:$runtime -w /tmp/$capture_file > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$CAPTURE_COMMAND"

    #-----------------------------------------------Client traffic generation----------------------------------------------
    echo "Starting LSQUIC normal Client"
    LSQUIC_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./lsquic_client.sh 2 4 20 2 4 $url_l' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$LSQUIC_CLIENT_COMMAND"
    
    echo "Starting AIOQUIC normal Client"
    BASE_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./basesim.sh 4 5 $runtime 2 3 $url_a' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$BASE_CLIENT_COMMAND"

    echo "Starting Flooding Client"
    FLOOD_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_flood && source venv/bin/activate && ./flood.sh $min_con $max_con $runtime $url_a' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$FLOOD_COMMAND"

    sleep $runtime 

    #--------------------------------------------------------Analysis-------------------------------------------------------
    echo "Decryption of traffic"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/aioquic_base/aioquiclog" ./aioquiclog_temp 
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/aioquic_base/aioquiclog"
    cat aioquiclog_temp >> "$SECRETS_FILE"
    rm aioquiclog_temp
    FORMAT_KEYS="cd $SERVER_DIR/lsquic/bin && ./getlsquickeys.sh > /dev/null 2>&1"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$FORMAT_KEYS"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/lsquic/bin/final_keys.txt" ./lsquic_temp
    cat lsquic_temp >> "$SECRETS_FILE"
    rm lsquic_temp

    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "sudo chown $USER_SERVER:$USER_SERVER /tmp/$capture_file"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:/tmp/$capture_file" ./packet_capture/$capture_file
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm /tmp/$capture_file"
    
    echo "Store capture and keys"
    tshark -r ./packet_capture/$capture_file -o tls.keylog_file:$SECRETS_FILE -w $result_file
    #tshark -r $decrypted_file -o tls.keylog_file:$SECRETS_FILE -V > packet_capture/decrypted_output.txt 
    cp $SECRETS_FILE ./secrets_files/flood_con:"$min_con"-"$max_con"_time:"$runtime".txt
    rm $SECRETS_FILE && rm ./packet_capture/$capture_file
}   

simulate_slowloris(){
    local min_con=$1
    local max_con=$2
    local runtime=$3
    local min_sleep=$4
    local max_sleep=$5
    local url_a=https://$SERVER_IP:$AIOQUIC_PORT/index.html
    local url_l=https://$SERVER_IP:$LSQUIC_PORT/index.html
    local SECRETS_FILE="secrets.txt"
    local capture_file="simulation_capture.pcap"
    local result_file="packet_capture/slowloris_con:"$min_con"-"$max_con"_sleep:"$min_sleep"-"max_sleep"_time:"$runtime".pcap"

    #-----------------------------------------------Server Setup and Capturing---------------------------------------------
    echo "Starting Aioquicserver on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && python3 examples/http3_server.py --certificate cert.pem --private-key key.pem --host $SERVER_IP --port $AIOQUIC_PORT -l aioquiclog ' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $AIOQUIC_PORT

    echo "Starting LSQUIC server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/lsquic/bin && ./http_server -c $SERVER_IP,fullchain.pem,privkey.pem -s 0.0.0.0:$LSQUIC_PORT -r /home/philipp/www/ -G /home/philipp/lsquic/bin/keys' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $LSQUIC_PORT

    echo "Capturing traffic on Port $LSQUIC_PORT and $AIQOUIC_PORT"
    CAPTURE_COMMAND="nohup sudo tshark -i $SERVER_INTERFACE -f 'port $AIOQUIC_PORT or port $LSQUIC_PORT' -a duration:$runtime -w /tmp/$capture_file > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$CAPTURE_COMMAND"

    #-----------------------------------------------Client traffic generation----------------------------------------------
    echo "Starting LSQUIC normal Client"
    LSQUIC_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./lsquic_client.sh 2 4 $runtime 2 4 $url_l' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$LSQUIC_CLIENT_COMMAND"
    
    echo "Starting AIOQUIC normal Client"
    BASE_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./basesim.sh 4 5 $runtime 2 3 $url_a' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$BASE_CLIENT_COMMAND"

    echo "Starting Slowloris Client"
    FLOOD_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_loris && source venv/bin/activate && ./slowloris.sh $min_con $max_con $runtime $min_sleep $max_sleep $url_a' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$FLOOD_COMMAND"

    sleep $runtime 

    #--------------------------------------------------------Analysis-------------------------------------------------------
    echo "Decryption of traffic"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/aioquic_base/aioquiclog" ./aioquiclog_temp 
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/aioquic_base/aioquiclog"
    cat aioquiclog_temp >> "$SECRETS_FILE"
    rm aioquiclog_temp
    FORMAT_KEYS="cd $SERVER_DIR/lsquic/bin && ./getlsquickeys.sh > /dev/null 2>&1"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$FORMAT_KEYS"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/lsquic/bin/final_keys.txt" ./lsquic_temp
    cat lsquic_temp >> "$SECRETS_FILE"
    rm lsquic_temp

    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "sudo chown $USER_SERVER:$USER_SERVER /tmp/$capture_file"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:/tmp/$capture_file" ./packet_capture/
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm /tmp/$capture_file"
    
    echo "Store capture and keys"
    tshark -r ./packet_capture/$capture_file -o tls.keylog_file:$SECRETS_FILE -w $result_file
    #tshark -r $decrypted_file -o tls.keylog_file:$SECRETS_FILE -V > packet_capture/decrypted_output.txt 
    cp $SECRETS_FILE ./secrets_files/slowloris_con:"$min_con"-"$max_con"_sleep:"$min_sleep"-"max_sleep"_time:"$runtime".txt
    rm $SECRETS_FILE && rm ./packet_capture/$capture_file
}   

simulate_normal(){
    local runtime=$1
    local url_a=https://$SERVER_IP:$AIOQUIC_PORT/index.html
    local url_l=https://$SERVER_IP:$LSQUIC_PORT/index.html
    local SECRETS_FILE="secrets.txt"
    local capture_file="simulation_capture.pcap"
    local result_file="packet_capture/normal_time:"$runtime"_decrypted.pcap"

    #-----------------------------------------------Server Setup and Capturing---------------------------------------------
    echo "Starting Aioquicserver on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && python3 examples/http3_server.py --certificate cert.pem --private-key key.pem --host $SERVER_IP --port $AIOQUIC_PORT -l aioquiclog ' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $AIOQUIC_PORT

    echo "Starting LSQUIC server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/lsquic/bin && ./http_server -c $SERVER_IP,fullchain.pem,privkey.pem -s 0.0.0.0:$LSQUIC_PORT -r /home/philipp/www/ -G $SERVER_DIR/lsquic/bin/keys' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $LSQUIC_PORT

    echo "Capturing traffic on Port $LSQUIC_PORT and $AIQOUIC_PORT"
    CAPTURE_COMMAND="nohup sudo tshark -i $SERVER_INTERFACE -f 'port $AIOQUIC_PORT or port $LSQUIC_PORT' -a duration:$runtime -w /tmp/$capture_file > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$CAPTURE_COMMAND"

    #-----------------------------------------------Client traffic generation----------------------------------------------
    echo "Starting LSQUIC normal Client"
    LSQUIC_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./lsquic_client.sh 2 4 $runtime 2 4 $url_l' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$LSQUIC_CLIENT_COMMAND"
    
    echo "Starting AIOQUIC normal Client"
    BASE_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./basesim.sh 4 5 $runtime 2 3 $url_a' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$BASE_CLIENT_COMMAND"

    sleep $runtime 

    #--------------------------------------------------------Analysis-------------------------------------------------------
    echo "Decryption of traffic"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/aioquic_base/aioquiclog" ./aioquiclog_temp 
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/aioquic_base/aioquiclog"
    cat aioquiclog_temp >> "$SECRETS_FILE"
    rm aioquiclog_temp
    FORMAT_KEYS="cd $SERVER_DIR/lsquic/bin && ./getlsquickeys.sh > /dev/null 2>&1"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$FORMAT_KEYS"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/lsquic/bin/final_keys.txt" ./lsquic_temp
    cat lsquic_temp >> "$SECRETS_FILE"
    rm lsquic_temp

    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "sudo chown $USER_SERVER:$USER_SERVER /tmp/$capture_file"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:/tmp/$capture_file" ./packet_capture/
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm /tmp/$capture_file"
    
    echo "Store capture and keys"
    tshark -r ./packet_capture/$capture_file -o tls.keylog_file:$SECRETS_FILE -w $result_file
    #tshark -r $decrypted_file -o tls.keylog_file:$SECRETS_FILE -V > packet_capture/decrypted_output.txt 
    cp $SECRETS_FILE ./secrets_files/normal_time:"$runtime"_decrypted.txt
    rm $SECRETS_FILE && rm ./packet_capture/$capture_file
}   

simulate_lsquic_http3(){
echo "test"
}

#simulate_flood 10 15 20

#simulate_slowloris 10 14 20 2 4

simulate_normal 20