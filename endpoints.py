from resources.api import api
from resources.monitoring import lsd_fee_recipient, validator_fee_recipient 


# It adds endpoints to the app
class EndPoints:
    """
    Add endpoints to the api by including the routers
    """

    def __init__(self, app):
        """
        It adds endpoints to the app
        
        :param app: The Flask application instance
        """
        self.app = app
        self.add_endpoints()

    def add_endpoints(self):
        """
        It adds all endpoints defined in routers in resources
        """
        self.app.include_router(api.router)
        self.app.include_router(lsd_fee_recipient.router)
        self.app.include_router(validator_fee_recipient.router)


