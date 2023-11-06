# Secure / remove RPC portmapper service

```Shell
sudo netstat -apn | grep LISTEN
# shows
tcp        0      0 0.0.0.0:111             0.0.0.0:*               LISTEN      1/systemd
```

```Shell
grep 111 /etc/services
# shows
sunrpc          111/tcp         portmapper      # RPC 4.0 portmapper
sunrpc          111/udp         portmapper
```

```Shell
rpcinfo -p
# shows
   program vers proto   port  service
    100000    4   tcp    111  portmapper
    100000    3   tcp    111  portmapper
    100000    2   tcp    111  portmapper
    100000    4   udp    111  portmapper
    100000    3   udp    111  portmapper
    100000    2   udp    111  portmapper
```

```Shell
systemctl status rpcbind
sudo systemctl disable rpcbind rpcbind.socket
```
