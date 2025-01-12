# Steps to Deploy

```
sudo apt install python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools
sudo apt install python3-venv
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

/etc/systemd/system/capsules.service
```
[Unit]
Description=uWSGI instance to serve capsules
After=network.target

[Service]
User=defossez
Group=www-data
WorkingDirectory=/opt/capsules
Environment="PATH=/opt/capsules/env/bin"
ExecStart=/opt/capsules/env/bin/uwsgi --ini capsules.ini

[Install]
WantedBy=multi-user.target
```

```
sudo systemctl start capsules
sudo systemctl enable capsules
sudo systemctl status capsules
```


/etc/nginx/nginx.conf
```
server {
    listen 80;
    server_name capsules.florandefossez.com;

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/opt/capsules/capsules.sock;
    }
}
```
