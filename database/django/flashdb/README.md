## Start development server on external facing interface (usually 146.118.64.208) with:
sudo python3 manage.py runserver `ip -o route get to 150.229.69.37 | sed -n 's/.*src \([0-9.]\+\).*/\1/p' `:80 --insecure

## Start and disconnect from terminal:
sudo setsid python3 manage.py runserver `ip -o route get to 150.229.69.37 | sed -n 's/.*src \([0-9.]\+\).*/\1/p' `:80 --insecure 1>out_server.log 2>err_server.log

## Start and disconnect sslserver from terminal:
sudo setsid python3 manage.py runsslserver `ip -o route get to 150.229.69.37 | sed -n 's/.*src \([0-9.]\+\).*/\1/p' `:443 --certificate /etc/letsencrypt/live/flash.aussrc.org/fullchain.pem --key /etc/letsencrypt/live/flash.aussrc.org/privkey.pem 1>out_server.log 2>err_server.log

