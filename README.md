# --
Edit domain.list file with your domains, script will try to find all ec2 instances associated with domains in file.

Run with bash or use run.sh file in repo:
```bash
chmod +x ./cleanup_instances.py
./cleanup_instances.py
```
Program output:
```bash
[instanceid] [imageid] [publicdnsname] [instancestatus] [dnshealth] 
```
