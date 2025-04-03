from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.core.exceptions import PermissionDenied


def unauthenticated_user(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/')
        else:
            return view_func(request, *args, **kwargs)
    return wrapper_func


def allowed_users(allowed_roles=[]):
    def decorator(view_func):
        def wrapper_func(request, *args, **kwargs):

            groups = None
            if request.user.groups.exists():
                groups = request.user.groups.all()
                name = None
                for group in groups:
                    name_in = group.name
                    if name_in in allowed_roles:
                        name = name_in
                if name is not None:
                    return view_func(request, *args, **kwargs)
                else:
                    return HttpResponse('<h1>Ви не можете переглянути цю сторінку</h1>')

        return wrapper_func
    return decorator


def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            user_role = request.user.get_role()
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            messages.error(request, 'You do not have permission to access this page.')
            raise PermissionDenied
        return _wrapped_view
    return decorator

# Convenience decorators for specific roles
def admin_required(view_func):
    return role_required(['admin'])(view_func)

def employee_required(view_func):
    return role_required(['admin', 'empl'])(view_func)

def client_required(view_func):
    return role_required(['client'])(view_func)

def engineer_required(view_func):
    return role_required(['admin', 'engineer'])(view_func)


