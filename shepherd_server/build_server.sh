sudo systemctl stop shepherd-redirect
sudo systemctl stop shepherd-scheduler
sudo systemctl stop shepherd-api
#
sudo pkill shepherd-*
#
sudo -E ~/.local/bin/uv tool uninstall shepherd-server
~/.local/bin/uv tool install git+https://github.com/nes-lab/shepherd-webapi.git@main#subdirectory=shepherd_server --force
# note: universal in comparison to `uv tool upgrade`
#
sudo systemctl start mongod
sudo systemctl start shepherd-redirect
sudo systemctl start shepherd-scheduler
sudo systemctl start shepherd-api
#
~/.local/bin/uv cache prune
# uv cache clean
