#! /bin/bash

source .venv/bin/activate

cd merged

python main.py &
streamlit run streamlit_ui.py &
streamlit run upload_ui.py --server.port 8502