docker run -it --rm --ipc=host \
    -v /mnt/sda1/DJ/code:/root/code \
    -v /mnt/sda1/DJ/data:/root/data \
    -v /mnt/12T:/root/public \
    -p 7001:22 \
    --gpus all\
    --name loftr \
    pytorch:LoFTR
