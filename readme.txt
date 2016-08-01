This is an example of connecting to Privakey using the Python OIC library.
The sample uses CherryPy as its web framework.
This project uses the pyoidc library (https://github.com/rohe/pyoidc).

Requirements:
oic 0.7.6+
pyjwkest 1.0.1+
cherrypy 3.2.4+
pyaml 15.03.1+
cffi 1.4.1+


Directory Structure:
src : root of the project
certs : self-signed SSL cert for CherryPy local server
htdocs : web pages and resources for the project
rp.py : sample relying party showing how to communicate with Privakey
settings.yaml.example : configuration file for the server and Privakey connection settings


Registering with Privakey:
Download Privakey from the app store and register
Go to privakey.com and sign in
Sign up your company and create a new relying party
The redirect URIs that you will use:
  Use 1 for implicit flow, 2 for code flow, or both if switching during testing:
  1. https://localhost:80/implicit_flow
  2. https://localhost:80/code_flow

Open the settings.yaml.example and set your client id and client secret.

Setting up the Sample project:
Install Python 2.7 or later
Install dependencies (sudo apt-get install python-pip python-dev build-essential libssl-dev libsasl2-dev)

Browse to the simple_rp folder and run:
pip install -r requirements.txt

To run the server, browse to the simple_rp/src directory and run:
sudo python rp.py settings.yaml.example

This will start a local server at https://localhost:80
Enter your Privakey login to start the process.
