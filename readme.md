# PrivaKeySDK #

## Overview ##

This Python Example is intended to aid developers in implementing privaKey Authentication services in their service.

It is provided "as-is" without warranty, implicit or explicit. This and other libraries are provided as samples only.

For more information visit [www.privakey.com](https://www.privakey.com) or contact support@privakey.com

## Prerequisites ##

*python 2.7+ python-pip python-dev build-essential libssl-dev libsasl2-dev
*oic 0.7.6+
*pyjwkest 1.0.1+
*cherrypy 3.2.4+
*pyaml 15.03.1+
*cffi 1.4.1+

## Usage ##

Download the Privakey application from the Apple Store or the Google Play store.
Goto [Privakey.com](https://www.privakey.com) and sign up to become a relying party
Set your redirect url's:
'''
Use 1 for implicit flow, 2 for code flow, or both if switching during testing:
1. https://localhost:80/implicit_flow
2. https://localhost:80/code_flow
'''

Open the settings.yaml.example and set your client id and client secret.
Install the required dependances

'pip install -r requirements.txt'

You can run the sample:
'sudo python rp.py settings.yaml.example'

This will start a local server at https://localhost:80
Enter your Privakey login to start the process.
