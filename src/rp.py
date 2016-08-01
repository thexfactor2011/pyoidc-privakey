import argparse

import cherrypy
import string
import random
import os
from oic.oic import Client
from oic.oic.message import AuthorizationResponse
from oic.oic.message import RegistrationResponse
from oic.oic.message import IdToken
from oic.utils.authn.client import CLIENT_AUTHN_METHOD
import yaml

__author__ = 'hanuszewski@privakey.com'


class OIDCExampleRP(object):
    def __init__(self, client_metadata, behaviour):
        self.client_metadata = client_metadata
        self.behaviour = behaviour

        self.redirect_uri = self.client_metadata["redirect_uris"][0]        
        self.response_type = self.client_metadata["response_types"][0]
        self.behaviour = self.behaviour
   

    def rndstr(self, size=16):
        """
        Returns a string of random ascii characters or digits

        :param size: The length of the string
        :return: string
        """
        _basech = string.ascii_letters + string.digits
        return "".join([random.choice(_basech) for _ in range(size)])


    #Load the IDP client configuration
    #The url is the root of the IDP endpoints
    def dynamic_provider_info(self, session, url):
        issuer_url = url
        provider_info = session["client"].provider_config(issuer_url)#Hits the IDP to return the provider config
	client_info = {"client_id" : self.client_metadata["client_id"], "client_secret" : self.client_metadata["client_secret"]} #You must pre-register the relying party on privakey.com and provide the client id and secret from a config.
        #Manually registers the client object
        client_reg = RegistrationResponse(**client_info)
        session["client"].client_info = client_reg
        #Set the client secret
        session["client"].set_client_secret(session["client"].client_info["client_secret"])        
        

    #Makes the authentication request to the IDP
    #Returns the Countdown page or an error
    #Privakey recommends using code flow for server configurations
    #and implicit flow for clientside configurations.
    def make_authentication_request(self, session, email):
        session["state"] = self.rndstr(16)
        session["nonce"] = self.rndstr(16)
        
	request_args = {
            "response_type": self.response_type,
            "state": session["state"],
            "nonce": session["nonce"],
            "login_hint": email,
            "redirect_uri": self.redirect_uri,
            "client_id": session["client"].client_info["client_id"]
        }
	#Privakey only supports form_post type for implicit mode
        #If you were using code flow the response type would be code
	if "id_token" in self.response_type:
	   request_args.update({"response_mode":"form_post"})

        request_args.update(self.behaviour)

        auth_req = session["client"].construct_AuthorizationRequest(
            request_args=request_args)
                
        login_url = auth_req.request(session["client"].authorization_endpoint)
        return login_url
        

    #This parses the query string from the code flow and validates the tokens
    def parse_authentication_response(self, session, query_string, sformat="urlencoded"):
        auth_response = session["client"].parse_response(AuthorizationResponse,
                                                         info=query_string,
                                                         sformat=sformat)

        if auth_response["state"] != session["state"]:
            raise "The OIDC state does not match."

        if "id_token" in auth_response and \
                        auth_response["id_token"]["nonce"] != session["nonce"]:
            raise "The OIDC nonce does not match."

        return auth_response


    #This takes the code flow code and returns the access_token 
    #used to get the user info
    def make_token_request(self, session, auth_code):              
        args = {
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
            "client_id": session["client"].client_id,
            "client_secret": session["client"].client_secret
        }	
        
        token_response = session["client"].do_access_token_request(
            scope="openid",
            state=session[
                "state"],
            request_args=args,
            authn_method="client_secret_basic"
            )

        return token_response


    #This takes an access token and returns the user info from the Privakey IDP
    def make_userinfo_request(self, session, access_token):        
        userinfo_response = session["client"].do_user_info_request(
            token=access_token, method="GET")
        return userinfo_response


    
class RPServer(object):
    def __init__(self, client_metadata, behaviour, verify_ssl):
        self.rp = OIDCExampleRP(client_metadata, behaviour)
        self.verify_ssl = verify_ssl
        self.client_metadata = client_metadata

    #Loads the first html page of the project.
    @cherrypy.expose
    def index(self):
        return self._load_HTML_page_from_file("htdocs/index.html")


    #This gets called when you press the signin button.
    #The first step is to create the client object
    #Then we use the discovery endpoint to load all the info about the client
    #Finally make the authentication request and you will get back the countdown page
    #or an error if the client is misconfigured.
    @cherrypy.expose
    def authenticate(self, email):
        cherrypy.session["client"] = Client(verify_ssl=self.verify_ssl, client_authn_method=CLIENT_AUTHN_METHOD, client_id=self.client_metadata["client_id"])

	# Client discovery
        self.rp.dynamic_provider_info(cherrypy.session, url=self.client_metadata["IDP_URL"])
        
        # Make the authentication request. Returns the countdown page or error
        redirect_url = self.rp.make_authentication_request(cherrypy.session, email)
        raise cherrypy.HTTPRedirect(redirect_url, 302)

    
    #Handles the implicit flow response from the IDP
    #This returns an Id_token and a token that can be used to get the user info    
    @cherrypy.expose
    def implicit_flow(self, **kwargs):        
        if "error" in kwargs:
            cherrypy.request.show_tracebacks = False; #Set to true to show stacktrace
            error_message = "Authentication failed"
            if "error_description" in kwargs:
               error_message = kwargs["error_description"];
            raise cherrypy.HTTPError(500, "{}: {}".format(kwargs["error"], error_message))
	                                                               
        idt = IdToken().from_jwt(str(kwargs["id_token"]), verify=False)
	userinfo = self.rp.make_userinfo_request(cherrypy.session, kwargs["token"])
	
        html_page = self._load_HTML_page_from_file("htdocs/success_page.html")
        return html_page.format(idt, userinfo["sub"])


    #Handles the code flow response from the IDP 
    @cherrypy.expose
    def code_flow(self, **kwargs):
        if "error" in kwargs:
            cherrypy.request.show_tracebacks = False; #Set to true to show stacktrace
            error_message = "Authentication failed"
            if "error_description" in kwargs:
               error_message = kwargs["error_description"];
            raise cherrypy.HTTPError(500, "{}: {}".format(kwargs["error"], error_message))

        qs = cherrypy.request.query_string
        auth_response = self.rp.parse_authentication_response(cherrypy.session,
                                                              qs)
        auth_code = auth_response["code"]
        token_response = self.rp.make_token_request(cherrypy.session, auth_code)
               	
        userinfo = self.rp.make_userinfo_request(cherrypy.session, token_response["access_token"])        

        html_page = self._load_HTML_page_from_file("htdocs/success_page.html")        
        return html_page.format(token_response["id_token"], userinfo["sub"])

 
    #Finds and loads an html page from file
    def _load_HTML_page_from_file(self, path):
        if not path.startswith("/"): # relative path
            # prepend the root package dir
            path = os.path.join(os.path.dirname(__file__), path)

        with open(path, "r") as f:
            return f.read()



def main():    
    parser = argparse.ArgumentParser(description='Example OIDC Client.')
    parser.add_argument("-p", "--port", default=80, type=int)
    parser.add_argument("-b", "--base", default="https://localhost", type=str)
    parser.add_argument("settings")
    args = parser.parse_args()

    with open(args.settings, "r") as f:
        settings = yaml.load(f)

    base = args.base.rstrip("/")  # strip trailing slash if it exists
    baseurl = "{base}:{port}".format(base=base, port=args.port)
    registration_info = settings["registration_info"]
    # patch redirect_uris with proper base url
    registration_info["redirect_uris"] = [url.format(base=baseurl) for url in
                                          registration_info["redirect_uris"]]

    rp_server = RPServer(registration_info, settings["behaviour"],
                         settings["server"]["verify_ssl"])

    # Mount the WSGI callable object (app) on the root directory
    cherrypy.tree.mount(rp_server, "/")    
    
    css_handler = cherrypy.tools.staticdir.handler(section="/", dir=os.path.abspath('htdocs/css'))
    cherrypy.tree.mount(css_handler, '/css')

    root_images = cherrypy.tools.staticdir.handler(section="/", dir=os.path.abspath('htdocs/img'))
    cherrypy.tree.mount(root_images, '/img')

    # Set the configuration of the web server
    cherrypy.config.update({
        'tools.sessions.on': True,
        'server.socket_port': args.port,
        'server.socket_host': '0.0.0.0'
    })

    if baseurl.startswith("https://"):
        cherrypy.config.update({
            'server.ssl_module': 'pyopenssl',
            'server.ssl_certificate': settings["server"]["cert"],
            'server.ssl_private_key': settings["server"]["key"],
            'server.ssl_certificate_chain': settings["server"]["cert_chain"]
        })

    # Start the CherryPy WSGI web server
    cherrypy.engine.start()
    cherrypy.engine.block()


if __name__ == "__main__":
    main()
