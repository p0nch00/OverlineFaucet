# Polygon Network Faucet

Clone this repository
```bash
git clone https://github.com/Algo-VaultStaking/PolygonFaucet.git
```

Rename `config.ini.example` to `config.ini` and add details.

Currently, the max number of tokens is enabled, which will also deny a user if they already have more than the max number in their wallet. However, this does not restrict the number of requests they can make.
If you would like to restrict users from requesting multiple times, you will need a MySQL database (such as MySQL, MariaDB, etc). 

Add a .service file for easy start/stop functions

```bash
sudo cat > /etc/systemd/system/faucet.service << "EOF"
[Unit]
  Description=OverlineFaucet

[Service]
  ExecStart=/usr/bin/python3 /home/ubuntu/OverlineFaucet/main.py
  LimitNOFILE=4096

[Install]
  WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable faucet
sudo service faucet start
```

