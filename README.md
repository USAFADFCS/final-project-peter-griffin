IMPORTANT: Before this project is run, the file "Travel_agent_framework\multi_agent_runner_UPDATED.py" must be copied into ".venv\Lib\site-packages\fairlib\modules\agent\multi_agent_runner.py". This fixes some bugs caused by the fairllm code.
IMPORTANT: To run the code in the browser the libraries in "backend\requirements.txt" must be installed to the virtual environment you are using.
IMPORTANT: You will need API keys for the flight and hotel tools, these are production keys which I requested from the API provider. I will send those to you so that they are not uploaded to github.

To run the agent in the terminal type
  python Travel_agent_framework\travel_multi_agent.py

To run this in a browser type
  uvicorn backend.app:app --reload
and then navigate to 127.0.0.1:8000

Design choices are explained in the report, I'm not sure why the AI that wrote the assignment asked for it in the README file as well...
