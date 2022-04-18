#!/bin/bash

# This script opens or creates a tmux session with panes to run the Django,
# Notebook, Redis and Ngrok servers. The tmux sessions continue to run after
# the shell window is closed.
# Some default commands are:
# Switch pane:    Ctrl-b ARROW_KEY
# Kill pane:      Ctrl-b x y
# Resize pane:    Ctrl-b esc ARROW_KEY

# To give script execute permission: chmod u+x runServer.sh
# Adjust REDIS_DIR and NGROK_DIR as necessary.

SCRIPT_DIR="${0%/*}"
REDIS_DIR="../supporting-software/redis-4.0.1/"
NGROK_DIR="../supporting-software/"

#Alternative to get script dir:
#DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to script directory to activate virtual environment:
# (Tmux session automatically uses venv from which it was launched)
cd $SCRIPT_DIR
source venv/bin/activate

tmux start-server
# -A flag: attaches session if it already exists otherwise creates new:
tmux new-session -c $SCRIPT_DIR -A -d -s CrisisDataApp -n Shell1 -d "/usr/bin/env sh -c \"python manage.py runserver\"; /usr/bin/env sh -i"
tmux split-window -c "${SCRIPT_DIR}/notebooks" -t CrisisDataApp:0 "/usr/bin/env sh -c \"../manage.py shell_plus --notebook\"; /usr/bin/env sh -i"
tmux split-window -c $REDIS_DIR -t CrisisDataApp:0 "/usr/bin/env sh -c \"./src/redis-server\"; /usr/bin/env sh -i"
tmux split-window -c $NGROK_DIR -t CrisisDataApp:0 "/usr/bin/env sh -c \"./ngrok http 8000\"; /usr/bin/env sh -i"
#tmux split-window -c $SCRIPT_DIR -t CrisisDataApp:0 "/usr/bin/env sh -c \"python manage.py shell\"; /usr/bin/env sh -i"
tmux select-layout -t CrisisDataApp:0 tiled
tmux attach -t CrisisDataApp


# Send commands to window:
#tmux send -t CrisisDataApp.0 ls ENTER
