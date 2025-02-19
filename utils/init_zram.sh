sudo swapoff -a
sudo zramctl --reset /dev/zram0
sudo modprobe -r zram
sudo modprobe zram
echo 1 | sudo tee /sys/class/zram-control/hot_add
ls /dev/zram*
echo lz4 | sudo tee /sys/block/zram0/comp_algorithm
echo $((50 * 1024 * 1024 * 1024)) | sudo tee /sys/block/zram0/disksize
sudo mkswap /dev/zram0
sudo swapon /dev/zram0 -p 100
