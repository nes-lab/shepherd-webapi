sudo systemctl stop shepherd-redirect
sudo systemctl stop shepherd-scheduler
sudo systemctl stop shepherd-api
sudo pkill shepherd-*
uv tool install --with git+https://github.com/nes-lab/shepherd@dev#subdirectory=software/shepherd-herd --with git+https://github.com/nes-lab/shepherd-tools@dev#>sudo systemctl start mongod
sudo systemctl start shepherd-redirect
sudo systemctl start shepherd-scheduler
sudo systemctl start shepherd-api
uv cache prune
# uv cache clean
