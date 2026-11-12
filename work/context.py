from .sso import local_login_allowed

def navigation(request):
    return {'section': request.resolver_match.url_name if request.resolver_match else '', 'local_login_allowed':local_login_allowed()}
