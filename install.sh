#!/data/data/com.termux/files/usr/bin/bash
pkg update -y
pkg install -y python termux-api
termux-setup-storage
echo "Готово. Запуск: python jarvis.py"
