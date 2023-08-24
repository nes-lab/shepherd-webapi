## Testbed Setup

### constraints

Server

- needs access to large datastorage with > 50 MB/s read/write speed
- internet-access (port 80, 443)
- ssh access (port 22) from outside and VLAN
- ptp (port 319, 320)

VLAN with nodes

- internet-access (port 80, 443)
- ssh access (port 22) from outside and VLAN
- ptp (port 319, 320)


## ICMP-Warnings

**Problem**

Centreon warns:

ICMP Timestamp Reply Information Disclosure 
SEVERITY: Low (2.1)
PORT: general/icmp
DESCR: The following response / ICMP packet has been received:
- ICMP Type: 14
- ICMP Code: 0


### Abschaltung des ICMP-Systems

[Source](https://askubuntu.com/questions/1182407/icmp-is-not-getting-disabled)

**Changes**

```Shell
sudo nano /etc/sysctl.conf
    net.ipv4.tcp_timestamps = 0
    net.ipv4.icmp_echo_ignore_all = 1
    net.ipv4.icmp_echo_ignore_broadcasts = 1
sudo nano /etc/ufw/sysctl.conf
    net.ipv4.icmp_echo_ignore_all=1
```

Restart (services)

**Test**

```Shell
cat /proc/sys/net/ipv4/icmp_echo_ignore_all
# check for = 1
sudo sysctl -p
# shows active config
# nping (siehe unten) lieferte aber weiterhin responses
```

### Firewall-Filtering

[Source](https://www.golinuxcloud.com/disable-icmp-timestamp-responses-in-linux/)

**Changes** (Methode 1 von vielen)

```Shell
sudo iptables -A INPUT -p icmp --icmp-type timestamp-request -j DROP
sudo iptables -A OUTPUT -p icmp --icmp-type timestamp-reply -j DROP
```

**Test**

```Shell
sudo nping --icmp-type 13 -v <serverIP>
sudo nping --icmp-type 14 -v <serverIP>
```

**Reverse**

```Shell
sudo iptables --flush
sudo iptables --zero
sudo iptables --delete-chain
# test with
sudo iptables --list
sudo iptables --list-rules
```

or, following [this source](https://www.cyberciti.biz/tips/linux-iptables-how-to-flush-all-rules.html)

```Shell
# Accept all traffic first to avoid ssh lockdown  via iptables firewall rules #
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT
 
# Flush All Iptables Chains/Firewall rules #
iptables -F
 
# Delete all Iptables Chains #
iptables -X
 
# Flush all counters too #
iptables -Z 
# Flush and delete all nat and  mangle #
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X
iptables -t raw -F
iptables -t raw -X
```
