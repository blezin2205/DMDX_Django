from django.http import HttpResponse
from django.shortcuts import redirect


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


