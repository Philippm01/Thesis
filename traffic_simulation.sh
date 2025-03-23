USER_CLIENT=""
USER_SERVER=""

PASSWORD_CLIENT=""
PASSWORD_SERVER=""

CLIENT_IP=""
SERVER_IP=""

CLIENT_INTERFACE="wlan0"
SERVER_INTERFACE="wlan0"

AIOQUIC_PORT="4000"
LSQUIC_PORT="4001"
QUICLY_PORT="4002"

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

simulate_loris_traffic(){
    local min_con=$1
    local max_con=$2
    local runtime=$3
    local min_sleep=$4
    local max_sleep=$5
    local iteration=$6
    local url_a=https://$SERVER_IP:$AIOQUIC_PORT/index.html
    local url_l=https://$SERVER_IP:$LSQUIC_PORT/index.html
    local SECRETS_FILE="secrets.txt"
    local capture_file="simulation_capture.pcap"
    local result_file="packet_capture/slowloris_con:"$min_con"-"$max_con"_sleep:"$min_sleep"-"$max_sleep"_time:"$runtime"_it:"$iteration".pcap"

    #-----------------------------------------------Server Setup and Capturing---------------------------------------------
    echo "Starting Aioquicserver on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && python3 examples/http3_server.py --certificate cert.pem --private-key key.pem --host $SERVER_IP --port $AIOQUIC_PORT -l aioquiclog ' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $AIOQUIC_PORT

    echo "Starting LSQUIC server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/lsquic/bin && ./http_server -c $SERVER_IP,fullchain.pem,privkey.pem -s 0.0.0.0:$LSQUIC_PORT -r /home/philipp/www/ -G $SERVER_DIR/lsquic/bin/keys' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $LSQUIC_PORT

    echo "Starting QUICLY server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./cli -c server.crt -k server.key $SERVER_IP $QUICLY_PORT -l quiclykeylogfile.txt' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $QUICLY_PORT

    echo "Capturing traffic on Port $LSQUIC_PORT and $AIOQUIC_PORT and $QUICLY_PORT"
    CAPTURE_COMMAND="nohup sudo tshark -i $SERVER_INTERFACE -f 'port $AIOQUIC_PORT or port $LSQUIC_PORT or port $QUICLY_PORT' -a duration:$runtime -w /tmp/$capture_file -F pcap > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$CAPTURE_COMMAND"
    
    #-----------------------------------------------Client traffic generation----------------------------------------------
    echo "Starting LSQUIC normal Client"
    LSQUIC_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./lsquic_client.sh 5 10 $runtime 1 2 $url_l' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$LSQUIC_CLIENT_COMMAND"
    
    echo "Starting AIOQUIC normal Client"
    BASE_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./basesim.sh 5 10  $runtime 1 2 $url_a' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$BASE_CLIENT_COMMAND"

    echo "Starting QUICLY normal Client"
    QUICLY_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./quicly_base_sim.sh 5 10 $runtime 1 2 $SERVER_IP $QUICLY_PORT' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$QUICLY_CLIENT_COMMAND"
    
    echo "Starting Slowloris Client"
    FLOOD_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_loris && source venv/bin/activate && ./slowloris.sh $min_con $max_con $runtime $min_sleep $max_sleep $url_a' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$FLOOD_COMMAND"

    sleep $runtime 

    #--------------------------------------------------------Analysis-------------------------------------------------------
    echo "Decryption of traffic"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/aioquic_base/aioquiclog" ./aioquic_temp 
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/quicly/quiclykeylogfile.txt" ./quicly_temp
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/quicly/quiclykeylogfile.txt"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/aioquic_base/aioquiclog"

    FORMAT_KEYS="cd $SERVER_DIR/lsquic/bin && ./getlsquickeys.sh > /dev/null 2>&1"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$FORMAT_KEYS"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/lsquic/bin/final_keys.txt" ./lsquic_temp
    
    cat lsquic_temp >> "$SECRETS_FILE"
    cat aioquic_temp >> "$SECRETS_FILE"
    cat quicly_temp >> "$SECRETS_FILE"
    rm lsquic_temp
    rm aioquic_temp
    rm quicly_temp

    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "sudo chown $USER_SERVER:$USER_SERVER /tmp/$capture_file"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:/tmp/$capture_file" ./packet_capture/
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm /tmp/$capture_file"
    
    mv ./packet_capture/$capture_file $result_file
    cp $SECRETS_FILE ./secrets_files/slowloris_con:"$min_con"-"$max_con"_sleep:"$min_sleep"-"$max_sleep"_time:"$runtime"_it:"$iteration".txt
    rm $SECRETS_FILE && rm ./packet_capture/$capture_file
}   

simulate_flood_traffic(){
    local min_con=$1
    local max_con=$2
    local runtime=$3
    local iteration=$4
    local url_a=https://$SERVER_IP:$AIOQUIC_PORT/index.html
    local url_l=https://$SERVER_IP:$LSQUIC_PORT/index.html
    local SECRETS_FILE="secrets.txt"
    local capture_file="simulation_capture.pcap"
    local result_file="packet_capture/flood_con:"$min_con"-"$max_con"_time:"$runtime"_it:"$iteration".pcap"

    #-----------------------------------------------Server Setup and Capturing---------------------------------------------
    echo "Starting Aioquicserver on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && python3 examples/http3_server.py --certificate cert.pem --private-key key.pem --host $SERVER_IP --port $AIOQUIC_PORT -l aioquiclog ' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $AIOQUIC_PORT

    echo "Starting LSQUIC server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/lsquic/bin && ./http_server -c $SERVER_IP,fullchain.pem,privkey.pem -s 0.0.0.0:$LSQUIC_PORT -r /home/philipp/www/ -G $SERVER_DIR/lsquic/bin/keys' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $LSQUIC_PORT

    echo "Starting QUICLY server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./cli -c server.crt -k server.key $SERVER_IP $QUICLY_PORT -l quiclykeylogfile.txt' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $QUICLY_PORT

    echo "Capturing traffic on Port $LSQUIC_PORT and $AIOQUIC_PORT and $QUICLY_PORT"
    CAPTURE_COMMAND="nohup sudo tshark -i $SERVER_INTERFACE -f 'port $AIOQUIC_PORT or port $LSQUIC_PORT or port $QUICLY_PORT' -a duration:$runtime -w /tmp/$capture_file -F pcap > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$CAPTURE_COMMAND"
    
    #-----------------------------------------------Client traffic generation----------------------------------------------
    echo "Starting LSQUIC normal Client"
    LSQUIC_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./lsquic_client.sh 5 10 $runtime 1 2 $url_l' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$LSQUIC_CLIENT_COMMAND"
    
    echo "Starting AIOQUIC normal Client"
    BASE_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./basesim.sh 5 10  $runtime 1 2 $url_a' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$BASE_CLIENT_COMMAND"

    echo "Starting QUICLY normal Client"
    QUICLY_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./quicly_base_sim.sh 5 10 $runtime 1 2 $SERVER_IP $QUICLY_PORT' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$QUICLY_CLIENT_COMMAND"
    
    echo "Starting Flooding Client"
    FLOOD_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_flood && source venv/bin/activate && ./flood.sh $min_con $max_con $runtime $url_a' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$FLOOD_COMMAND"

    sleep $runtime 

    #--------------------------------------------------------Analysis-------------------------------------------------------
    echo "Decryption of traffic"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/aioquic_base/aioquiclog" ./aioquic_temp 
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/quicly/quiclykeylogfile.txt" ./quicly_temp
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/quicly/quiclykeylogfile.txt"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/aioquic_base/aioquiclog"

    FORMAT_KEYS="cd $SERVER_DIR/lsquic/bin && ./getlsquickeys.sh > /dev/null 2>&1"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$FORMAT_KEYS"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/lsquic/bin/final_keys.txt" ./lsquic_temp
    
    cat lsquic_temp >> "$SECRETS_FILE"
    cat aioquic_temp >> "$SECRETS_FILE"
    cat quicly_temp >> "$SECRETS_FILE"
    rm lsquic_temp
    rm aioquic_temp
    rm quicly_temp

    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "sudo chown $USER_SERVER:$USER_SERVER /tmp/$capture_file"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:/tmp/$capture_file" ./packet_capture/
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm /tmp/$capture_file"
    
    mv ./packet_capture/$capture_file $result_file
    cp $SECRETS_FILE ./secrets_files/flood_con:"$min_con"-"$max_con"_time:"$runtime"_it:"$iteration".txt
    rm $SECRETS_FILE && rm ./packet_capture/$capture_file
}   

simulate_normal_traffic(){
    local runtime=$1
    local iteration=$2
    local url_a=https://$SERVER_IP:$AIOQUIC_PORT/index.html
    local url_l=https://$SERVER_IP:$LSQUIC_PORT/index.html
    local SECRETS_FILE="secrets.txt"
    local capture_file="simulation_capture.pcap"
    local result_file="packet_capture/normal_time:"$runtime"_it:"$iteration".pcap"

    #-----------------------------------------------Server Setup and Capturing---------------------------------------------
    echo "Starting Aioquicserver on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && python3 examples/http3_server.py --certificate cert.pem --private-key key.pem --host $SERVER_IP --port $AIOQUIC_PORT -l aioquiclog ' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $AIOQUIC_PORT

    echo "Starting LSQUIC server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/lsquic/bin && ./http_server -c $SERVER_IP,fullchain.pem,privkey.pem -s 0.0.0.0:$LSQUIC_PORT -r /home/philipp/www/ -G $SERVER_DIR/lsquic/bin/keys' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $LSQUIC_PORT

    echo "Starting QUICLY server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./cli -c server.crt -k server.key $SERVER_IP $QUICLY_PORT -l quiclykeylogfile.txt' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $QUICLY_PORT

    echo "Capturing traffic on Port $LSQUIC_PORT and $AIOQUIC_PORT and $QUICLY_PORT"
    CAPTURE_COMMAND="nohup sudo tshark -i $SERVER_INTERFACE -f 'port $AIOQUIC_PORT or port $LSQUIC_PORT or port $QUICLY_PORT' -a duration:$runtime -w /tmp/$capture_file -F pcap > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$CAPTURE_COMMAND"
    
    #-----------------------------------------------Client traffic generation----------------------------------------------
    echo "Starting LSQUIC normal Client"
    LSQUIC_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./lsquic_client.sh 5 10 $runtime 1 2 $url_l' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$LSQUIC_CLIENT_COMMAND"
    
    echo "Starting AIOQUIC normal Client"
    BASE_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./basesim.sh 5 10  $runtime 1 2 $url_a' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$BASE_CLIENT_COMMAND"

    echo "Starting QUICLY normal Client"
    QUICLY_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./quicly_base_sim.sh 5 10 $runtime 1 2 $SERVER_IP $QUICLY_PORT' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$QUICLY_CLIENT_COMMAND"
    
    sleep $runtime 

    #--------------------------------------------------------Analysis-------------------------------------------------------
    echo "Decryption of traffic"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/aioquic_base/aioquiclog" ./aioquic_temp 
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/quicly/quiclykeylogfile.txt" ./quicly_temp
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/quicly/quiclykeylogfile.txt"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/aioquic_base/aioquiclog"

    FORMAT_KEYS="cd $SERVER_DIR/lsquic/bin && ./getlsquickeys.sh > /dev/null 2>&1"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$FORMAT_KEYS"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/lsquic/bin/final_keys.txt" ./lsquic_temp
    
    cat lsquic_temp >> "$SECRETS_FILE"
    cat aioquic_temp >> "$SECRETS_FILE"
    cat quicly_temp >> "$SECRETS_FILE"
    rm lsquic_temp
    rm aioquic_temp
    rm quicly_temp

    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "sudo chown $USER_SERVER:$USER_SERVER /tmp/$capture_file"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:/tmp/$capture_file" ./packet_capture/
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm /tmp/$capture_file"
    
    mv ./packet_capture/$capture_file $result_file
    cp $SECRETS_FILE ./secrets_files/normal_time:"$runtime"_it:"$iteration".txt
    rm $SECRETS_FILE && rm ./packet_capture/$capture_file
}   

simulate_lsquic_attack_traffic(){
    local runtime=$1
    local iteration=$2
    local num_attacks=$3  # New parameter
    local url_a=https://$SERVER_IP:$AIOQUIC_PORT/index.html
    local url_l=https://$SERVER_IP:$LSQUIC_PORT/index.html
    local SECRETS_FILE="secrets.txt"
    local capture_file="simulation_capture.pcap"
    local result_file="packet_capture/lsquic_attacks:"$num_attacks"_time:"$runtime"_it:"$iteration".pcap"

    #-----------------------------------------------Server Setup and Capturing---------------------------------------------
    echo "Starting Aioquicserver on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && python3 examples/http3_server.py --certificate cert.pem --private-key key.pem --host $SERVER_IP --port $AIOQUIC_PORT -l aioquiclog ' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $AIOQUIC_PORT

    echo "Starting LSQUIC server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/lsquic/bin && ./http_server -c $SERVER_IP,fullchain.pem,privkey.pem -s 0.0.0.0:$LSQUIC_PORT -r /home/philipp/www/ -G $SERVER_DIR/lsquic/bin/keys' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $LSQUIC_PORT

    echo "Starting QUICLY server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./cli -c server.crt -k server.key $SERVER_IP $QUICLY_PORT -l quiclykeylogfile.txt' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $QUICLY_PORT

    echo "Capturing traffic on Port $LSQUIC_PORT and $AIOQUIC_PORT and $QUICLY_PORT"
    CAPTURE_COMMAND="nohup sudo tshark -i $SERVER_INTERFACE -f 'port $AIOQUIC_PORT or port $LSQUIC_PORT or port $QUICLY_PORT' -a duration:$runtime -w /tmp/$capture_file -F pcap > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$CAPTURE_COMMAND"
    
    #-----------------------------------------------Client traffic generation----------------------------------------------
    echo "Starting LSQUIC normal Client"
    LSQUIC_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./lsquic_client.sh 5 10 $runtime 1 2 $url_l' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$LSQUIC_CLIENT_COMMAND"
    
    echo "Starting AIOQUIC normal Client"
    BASE_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./basesim.sh 5 10  $runtime 1 2 $url_a' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$BASE_CLIENT_COMMAND"

    echo "Starting QUICLY normal Client"
    QUICLY_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./quicly_base_sim.sh 5 10 $runtime 1 2 $SERVER_IP $QUICLY_PORT' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$QUICLY_CLIENT_COMMAND"
    
    offsets=()
    for x in $(seq 1 $num_attacks); do
    offsets+=( "$(shuf -i 1-$runtime -n1)" )
    done
    IFS=$'\n' offsets=($(sort -n <<<"${offsets[*]}"))
    unset IFS
    start_time=$(date +%s)
    for offset in "${offsets[@]}"; do
    now=$(date +%s)
    elapsed=$(( now - start_time ))
    wait=$(( offset - elapsed ))
    [ "$wait" -gt 0 ] && sleep "$wait"
        echo "Starting LSQUIC Attack #$x"
        LSQUIC_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_http3CVE && source venv/bin/activate && timeout 1 ./http3attack.sh 1 1 3 1 1 $url_l' > /dev/null 2>&1 &"
        execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$LSQUIC_CLIENT_COMMAND"
        sleep 2
        SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/lsquic/bin && ./http_server -c $SERVER_IP,fullchain.pem,privkey.pem -s 0.0.0.0:$LSQUIC_PORT -r /home/philipp/www/ -G $SERVER_DIR/lsquic/bin/keys' > /dev/null 2>&1 &"
        execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    done

    sleep $((runtime - ($(date +%s) - start_time)))

    #--------------------------------------------------------Analysis-------------------------------------------------------
    echo "Decryption of traffic"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/aioquic_base/aioquiclog" ./aioquic_temp 
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/quicly/quiclykeylogfile.txt" ./quicly_temp
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/quicly/quiclykeylogfile.txt"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/aioquic_base/aioquiclog"

    FORMAT_KEYS="cd $SERVER_DIR/lsquic/bin && ./getlsquickeys.sh > /dev/null 2>&1"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$FORMAT_KEYS"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/lsquic/bin/final_keys.txt" ./lsquic_temp
    
    cat lsquic_temp >> "$SECRETS_FILE"
    cat aioquic_temp >> "$SECRETS_FILE"
    cat quicly_temp >> "$SECRETS_FILE"
    rm lsquic_temp
    rm aioquic_temp
    rm quicly_temp

    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "sudo chown $USER_SERVER:$USER_SERVER /tmp/$capture_file"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:/tmp/$capture_file" ./packet_capture/
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm /tmp/$capture_file"
    
    mv ./packet_capture/$capture_file $result_file
    cp $SECRETS_FILE ./secrets_files/lsquic_attacks:"$num_attacks"_time:"$runtime"_it:"$iteration".txt
    rm $SECRETS_FILE && rm ./packet_capture/$capture_file
}  

simulate_quicly_attack_traffic(){
    local runtime=$1
    local iteration=$2
    local num_attacks=$3  # New parameter
    local url_a=https://$SERVER_IP:$AIOQUIC_PORT/index.html
    local url_l=https://$SERVER_IP:$LSQUIC_PORT/index.html
    local SECRETS_FILE="secrets.txt"
    local capture_file="simulation_capture.pcap"
    local result_file="packet_capture/quicly_attacks:"$num_attacks"_time:"$runtime"_it:"$iteration".pcap"

    #-----------------------------------------------Server Setup and Capturing---------------------------------------------
    echo "Starting Aioquicserver on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && python3 examples/http3_server.py --certificate cert.pem --private-key key.pem --host $SERVER_IP --port $AIOQUIC_PORT -l aioquiclog ' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $AIOQUIC_PORT

    echo "Starting LSQUIC server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/lsquic/bin && ./http_server -c $SERVER_IP,fullchain.pem,privkey.pem -s 0.0.0.0:$LSQUIC_PORT -r /home/philipp/www/ -G $SERVER_DIR/lsquic/bin/keys' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $LSQUIC_PORT

    echo "Starting QUICLY server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./cli -c server.crt -k server.key $SERVER_IP $QUICLY_PORT -l quiclykeylogfile.txt' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $QUICLY_PORT

    echo "Capturing traffic on Port $LSQUIC_PORT and $AIOQUIC_PORT and $QUICLY_PORT"
    CAPTURE_COMMAND="nohup sudo tshark -i $SERVER_INTERFACE -f 'port $AIOQUIC_PORT or port $LSQUIC_PORT or port $QUICLY_PORT' -a duration:$runtime -w /tmp/$capture_file -F pcap > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$CAPTURE_COMMAND"
    
    #-----------------------------------------------Client traffic generation----------------------------------------------
    echo "Starting LSQUIC normal Client"
    LSQUIC_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./lsquic_client.sh 5 10 $runtime 1 2 $url_l' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$LSQUIC_CLIENT_COMMAND"
    
    echo "Starting AIOQUIC normal Client"
    BASE_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./basesim.sh 5 10  $runtime 1 2 $url_a' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$BASE_CLIENT_COMMAND"

    echo "Starting QUICLY normal Client"
    QUICLY_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./quicly_base_sim.sh 5 10 $runtime 1 2 $SERVER_IP $QUICLY_PORT' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$QUICLY_CLIENT_COMMAND"
    
    offsets=()
    for x in $(seq 1 $num_attacks); do
    offsets+=( "$(shuf -i 1-$runtime -n1)" )
    done
    IFS=$'\n' offsets=($(sort -n <<<"${offsets[*]}"))
    unset IFS
    start_time=$(date +%s)
    for offset in "${offsets[@]}"; do
    now=$(date +%s)
    elapsed=$(( now - start_time ))
    wait=$(( offset - elapsed ))
    [ "$wait" -gt 0 ] && sleep "$wait"
        echo "Starting QUICLY Attack #$x"
        LSQUIC_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/assertion_quicly && python3 quicly_assertion_script.py --ip $SERVER_IP --dport $QUICLY_PORT --sport-min 5000 --sport-max 8000' > /dev/null 2>&1 &"
        execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$LSQUIC_CLIENT_COMMAND"
        sleep 2
        SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./cli -c server.crt -k server.key $SERVER_IP $QUICLY_PORT -l quiclykeylogfile.txt' > /dev/null 2>&1 &"
        execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    done

    sleep $((runtime - ($(date +%s) - start_time)))

    #--------------------------------------------------------Analysis-------------------------------------------------------
    echo "Decryption of traffic"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/aioquic_base/aioquiclog" ./aioquic_temp 
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/quicly/quiclykeylogfile.txt" ./quicly_temp
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/quicly/quiclykeylogfile.txt"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/aioquic_base/aioquiclog"

    FORMAT_KEYS="cd $SERVER_DIR/lsquic/bin && ./getlsquickeys.sh > /dev/null 2>&1"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$FORMAT_KEYS"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/lsquic/bin/final_keys.txt" ./lsquic_temp
    
    cat lsquic_temp >> "$SECRETS_FILE"
    cat aioquic_temp >> "$SECRETS_FILE"
    cat quicly_temp >> "$SECRETS_FILE"
    rm lsquic_temp
    rm aioquic_temp
    rm quicly_temp
    
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "sudo chown $USER_SERVER:$USER_SERVER /tmp/$capture_file"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:/tmp/$capture_file" ./packet_capture/
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm /tmp/$capture_file"
    
    mv ./packet_capture/$capture_file $result_file
    cp $SECRETS_FILE ./secrets_files/quicly_attacks:"$num_attacks"_time:"$runtime"_it:"$iteration".txt
    rm $SECRETS_FILE && rm ./packet_capture/$capture_file
}  

simulate_quicly_attack_traffic_isolated(){
    local runtime=$1
    local iteration=$2
    local url_a=https://$SERVER_IP:$AIOQUIC_PORT/index.html
    local url_l=https://$SERVER_IP:$LSQUIC_PORT/index.html
    local SECRETS_FILE="secrets.txt"
    local capture_file="simulation_capture.pcap"
    local result_file="packet_capture/quicly_isolation_time:"$runtime"_it:"$iteration".pcap"

    #-----------------------------------------------Server Setup and Capturing---------------------------------------------

    echo "Starting QUICLY server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./cli -c server.crt -k server.key $SERVER_IP $QUICLY_PORT -l quiclykeylogfile.txt' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"

    echo "Capturing traffic on Port $LSQUIC_PORT and $AIOQUIC_PORT and $QUICLY_PORT"
    CAPTURE_COMMAND="nohup sudo tshark -i $SERVER_INTERFACE -f 'port $AIOQUIC_PORT or port $LSQUIC_PORT or port $QUICLY_PORT' -a duration:$runtime -w /tmp/$capture_file -F pcap > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$CAPTURE_COMMAND"
    
    #-----------------------------------------------Client traffic generation----------------------------------------------

    echo "Starting QUICLY normal Client"
    QUICLY_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./quicly_base_sim.sh 5 10 $runtime 1 2 $SERVER_IP $QUICLY_PORT' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$QUICLY_CLIENT_COMMAND"
    
    start_time=$(date +%s)
    while true; do
        now=$(date +%s)
        elapsed=$(( now - start_time ))
        if [ "$elapsed" -ge "$runtime" ]; then
            break
        fi
        
        LSQUIC_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/assertion_quicly && python3 quicly_assertion_script.py --ip $SERVER_IP --dport $QUICLY_PORT --sport-min 5000 --sport-max 8000' > /dev/null 2>&1 &"
        execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$LSQUIC_CLIENT_COMMAND"
        SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/quicly && ./cli -c server.crt -k server.key $SERVER_IP $QUICLY_PORT -l quiclykeylogfile.txt' > /dev/null 2>&1 &"
        execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    done

    #--------------------------------------------------------Analysis-------------------------------------------------------
    echo "Decryption of traffic"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/quicly/quiclykeylogfile.txt" ./quicly_temp
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/quicly/quiclykeylogfile.txt"

    cat quicly_temp >> "$SECRETS_FILE"
    rm quicly_temp
    
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "sudo chown $USER_SERVER:$USER_SERVER /tmp/$capture_file"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:/tmp/$capture_file" ./packet_capture/
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm /tmp/$capture_file"
    
    mv ./packet_capture/$capture_file $result_file
    cp $SECRETS_FILE ./secrets_files/quicly_isolation_time:"$runtime"_it:"$iteration".txt
    rm $SECRETS_FILE && rm ./packet_capture/$capture_file
}

simulate_lsquic_attack_traffic_isolated(){
    local runtime=$1
    local iteration=$2
    local url_a=https://$SERVER_IP:$AIOQUIC_PORT/index.html
    local url_l=https://$SERVER_IP:$LSQUIC_PORT/index.html
    local SECRETS_FILE="secrets.txt"
    local capture_file="simulation_capture.pcap"
    local result_file="packet_capture/lsquic_isolation_time:"$runtime"_it:"$iteration".pcap"

    #-----------------------------------------------Server Setup and Capturing---------------------------------------------

    echo "Starting LSQUIC server on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/lsquic/bin && ./http_server -c $SERVER_IP,fullchain.pem,privkey.pem -s 0.0.0.0:$LSQUIC_PORT -r /home/philipp/www/ -G $SERVER_DIR/lsquic/bin/keys' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"

    echo "Capturing traffic on Port $LSQUIC_PORT and $AIOQUIC_PORT and $QUICLY_PORT"
    CAPTURE_COMMAND="nohup sudo tshark -i $SERVER_INTERFACE -f 'port $AIOQUIC_PORT or port $LSQUIC_PORT or port $QUICLY_PORT' -a duration:$runtime -w /tmp/$capture_file -F pcap > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$CAPTURE_COMMAND"
    
    #-----------------------------------------------Client traffic generation----------------------------------------------

    echo "Starting LSQUIC normal Client"
    LSQUIC_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && ./lsquic_client.sh 5 10 $runtime 1 2 $url_l' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$LSQUIC_CLIENT_COMMAND"
    
    start_time=$(date +%s)
    while true; do
        now=$(date +%s)
        elapsed=$(( now - start_time ))
        if [ "$elapsed" -ge "$runtime" ]; then
            break
        fi
        
        LSQUIC_CLIENT_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_http3CVE && source venv/bin/activate && timeout 1 ./http3attack.sh 1 1 3 1 1 $url_l' > /dev/null 2>&1 &"
        execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$LSQUIC_CLIENT_COMMAND"
        SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/lsquic/bin && ./http_server -c $SERVER_IP,fullchain.pem,privkey.pem -s 0.0.0.0:$LSQUIC_PORT -r /home/philipp/www/ -G $SERVER_DIR/lsquic/bin/keys' > /dev/null 2>&1 &"
        execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    done

    #--------------------------------------------------------Analysis-------------------------------------------------------
    echo "Decryption of traffic"
    FORMAT_KEYS="cd $SERVER_DIR/lsquic/bin && ./getlsquickeys.sh > /dev/null 2>&1"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$FORMAT_KEYS"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/lsquic/bin/final_keys.txt" ./lsquic_temp
    
    cat lsquic_temp >> "$SECRETS_FILE"
    rm lsquic_temp

    
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "sudo chown $USER_SERVER:$USER_SERVER /tmp/$capture_file"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:/tmp/$capture_file" ./packet_capture/
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm /tmp/$capture_file"
    
    mv ./packet_capture/$capture_file $result_file
    cp $SECRETS_FILE ./secrets_files/lsquic_isolation_time:"$runtime"_it:"$iteration".txt
}

simulate_loris_traffic_isolation(){
    local min_con=$1
    local max_con=$2
    local runtime=$3
    local min_sleep=$4
    local max_sleep=$5
    local iteration=$6
    local url_a=https://$SERVER_IP:$AIOQUIC_PORT/index.html
    local url_l=https://$SERVER_IP:$LSQUIC_PORT/index.html
    local SECRETS_FILE="secrets.txt"
    local capture_file="simulation_capture.pcap"
    local result_file="packet_capture/slowloris_isolated_con:"$min_con"-"$max_con"_sleep:"$min_sleep"-"$max_sleep"_time:"$runtime"_it:"$iteration".pcap"

    #-----------------------------------------------Server Setup and Capturing---------------------------------------------
    echo "Starting Aioquicserver on $SERVER_IP..."
    SERVER_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_base && source venv/bin/activate && python3 examples/http3_server.py --certificate cert.pem --private-key key.pem --host $SERVER_IP --port $AIOQUIC_PORT -l aioquiclog ' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$SERVER_COMMAND"
    kill_server $runtime $AIOQUIC_PORT

    echo "Capturing traffic on Port $LSQUIC_PORT and $AIOQUIC_PORT and $QUICLY_PORT"
    CAPTURE_COMMAND="nohup sudo tshark -i $SERVER_INTERFACE -f 'port $AIOQUIC_PORT or port $LSQUIC_PORT or port $QUICLY_PORT' -a duration:$runtime -w /tmp/$capture_file -F pcap > /dev/null 2>&1 &"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$CAPTURE_COMMAND"
    
    #-----------------------------------------------Client traffic generation----------------------------------------------

    echo "Starting Slowloris Client"
    FLOOD_COMMAND="nohup bash -c 'cd $SERVER_DIR/aioquic_loris && source venv/bin/activate && ./slowloris.sh $min_con $max_con $runtime $min_sleep $max_sleep $url_a' > /dev/null 2>&1 &"
    execute_ssh_command "$USER_CLIENT" "$CLIENT_IP" "$PASSWORD_CLIENT" "$FLOOD_COMMAND"

    sleep $runtime 

    #--------------------------------------------------------Analysis-------------------------------------------------------
    echo "Decryption of traffic"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/aioquic_base/aioquiclog" ./aioquic_temp 
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/quicly/quiclykeylogfile.txt" ./quicly_temp
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/quicly/quiclykeylogfile.txt"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm $SERVER_DIR/aioquic_base/aioquiclog"

    FORMAT_KEYS="cd $SERVER_DIR/lsquic/bin && ./getlsquickeys.sh > /dev/null 2>&1"
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "$FORMAT_KEYS"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:$SERVER_DIR/lsquic/bin/final_keys.txt" ./lsquic_temp
    
    cat lsquic_temp >> "$SECRETS_FILE"
    cat aioquic_temp >> "$SECRETS_FILE"
    cat quicly_temp >> "$SECRETS_FILE"
    rm lsquic_temp
    rm aioquic_temp
    rm quicly_temp

    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "sudo chown $USER_SERVER:$USER_SERVER /tmp/$capture_file"
    sshpass -p "$PASSWORD_SERVER" scp "$USER_SERVER@$SERVER_IP:/tmp/$capture_file" ./packet_capture/
    execute_ssh_command "$USER_SERVER" "$SERVER_IP" "$PASSWORD_SERVER" "rm /tmp/$capture_file"
    
    mv ./packet_capture/$capture_file $result_file
    cp $SECRETS_FILE ./secrets_files/slowloris_isolated_con:"$min_con"-"$max_con"_sleep:"$min_sleep"-"$max_sleep"_time:"$runtime"_it:"$iteration".txt
    rm $SECRETS_FILE && rm ./packet_capture/$capture_file
}  

generation_flood(){
    local runtime=180
    local total_iterations=100
    
    for ((i=51; i<=$total_iterations; i++)); do  
        print_in_box "Flooding simulation iteration $i"
        simulate_flood_traffic 20 50 $runtime $i
        rebooting
    done
}

generation_loris(){
    local runtime=180
    local total_iterations=100
    
    for ((i=1; i<=$total_iterations; i++)); do 
        print_in_box "Slowloris simulation iteration $i"
        simulate_loris_traffic 5 10 $runtime 20 40 $i  
        rebooting 
    done
}

generation_lsquic(){
    local runtime=180
    local iterations_per_attack=10
    
    for num_attacks in $(seq 2 2 20); do
        for ((i=1; i<=$iterations_per_attack; i++)); do
            print_in_box "LSQUIC CVE simulation iteration $i with $num_attacks attacks"
            simulate_lsquic_attack_traffic $runtime $i $num_attacks
            rebooting
        done
    done
}

generation_quicly(){
    local runtime=180
    local iterations_per_attack=10
    
    for num_attacks in $(seq 2 2 20); do
        for ((i=1; i<=$iterations_per_attack; i++)); do
            print_in_box "Quicly CVE simulation iteration $i with $num_attacks attacks"
            simulate_quicly_attack_traffic $runtime $i $num_attacks
            rebooting
        done
    done
}

generation_normal(){
    local runtime=180
    local total_iterations=100
    
    for ((i=1; i<=$total_iterations; i++)); do
        print_in_box "Normal simulation iteration $i"
        simulate_normal_traffic $runtime $i
        rebooting
    done
}

generation_quicly_isolated(){
    local runtime=100
    local iterations_per_attack=100
    
    for ((i=1; i<=$iterations_per_attack; i++)); do
        simulate_quicly_attack_traffic_isolated $runtime $i 
        rebooting
    done
}

generation_lsquic_isolated(){
    local runtime=100
    local iterations_per_attack=100
    
    for ((i=1; i<=$iterations_per_attack; i++)); do
        print_in_box "LSQUIC Isolation simulation iteration $i"
        simulate_lsquic_attack_traffic_isolated $runtime $i 
        rebooting
    done
}

generation_loris_isolated(){
    local runtime=100
    local iterations_per_attack=100
    
    for ((i=1; i<=$iterations_per_attack; i++)); do
        simulate_loris_traffic_isolation 5 10 $runtime 1 5 $i  
        rebooting
    done
}

