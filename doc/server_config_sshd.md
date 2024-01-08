# Secure SSHd


## Forbid Umac-64

Add to `/etc/ssh/sshd-config`

```Shell
# shepherd-security-settings, additional to above
Protocol 2
#RhostsRSAAuthentication no # -> deprecated

# forbid weak algorithms ("-" in front)
KexAlgorithms           -ecdh-sha2*
HostKeyAlgorithms       -ecda-sha2*
Ciphers                 -arcfour*
MACs                    -*umac-64*
```

restart with

```Shell
sudo systemctl restart sshd
```

Check with

```Shell
ssh -vv localhost
```

which still reports umac-64
But locally run

```Shell
sudo sshd -T | egrep 'ciphers|macs|kexalgo'
```

show success.
