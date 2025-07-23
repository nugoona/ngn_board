from flask import Blueprint

def create_blueprint(name, import_name):
    return Blueprint(name, import_name)

meta_ads_blueprint = create_blueprint("meta_ads", __name__)
cafe24_blueprint = create_blueprint("cafe24", __name__)
accounts_blueprint = create_blueprint("accounts", __name__)


