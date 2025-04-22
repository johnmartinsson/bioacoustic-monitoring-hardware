sudo systemctl disable --now fake-hwclock
sudo update-rc.d -f fake-hwclock remove
sudo apt-get remove fake-hwclock -y
sudo sed -i '/if \[ -e \/run\/systemd\/system \] ; then/,/\/sbin\/hwclock --rtc=$dev --hctosys/ s/^/#/' /lib/udev/hwclock-set
