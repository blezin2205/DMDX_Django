import asyncio
import datetime
import math

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, FileResponse
from django.urls import reverse
from django.db.models import Prefetch, prefetch_related_objects
from .decorators import unauthenticated_user, allowed_users
from .models import *
from .serializers import *
from datetime import date
from dateutil.relativedelta import relativedelta
from django.contrib.auth import authenticate, login, logout
from .filters import *
from .forms import *
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.core.paginator import Paginator
from django.db.models import *
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.conf import settings
from django.core.mail import send_mail

import os
from xlsxwriter.workbook import Workbook
from django_htmx.http import trigger_client_event
from django.contrib import messages
import requests
import pandas
import csv
import pymsteams
import plotly.express as px
from django.db.models import Sum, F
from .tasks import *
from .views import *
from celery_progress.backend import Progress
from celery.result import AsyncResult
import threading
import firebase_admin
from firebase_admin import credentials, storage
from urllib.parse import quote_plus
bucket = storage.bucket()

def upload_to_storage(request):

    blobs = bucket.list_blobs()
    files = []
    folders = []

    for blob in blobs:
        if blob.name.endswith('/'):
            # It's a folder
            folders.append({'name': blob.name})
        else:
            # It's a file
            files.append({'name': blob.name, 'url': blob.public_url})
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            blob = bucket.blob(file.name)
            blob.upload_from_file(file)
            return JsonResponse({'message': 'Upload successful'})
        else:
            return JsonResponse({'message': 'Form is not valid'}, status=400)
    else:
        form = UploadFileForm()
    return render(request, 'supplies/firebase_upload.html', {'form': form, 'files': files, 'folders': folders})

def upload_files(request):
    if request.method == 'POST' and request.FILES.getlist('files'):
        files = request.FILES.getlist('files')
        current_path = request.POST.get('current_path', '')

        for file in files:
            directory = current_path  # Use current_path as the directory path
            blob = bucket.blob(os.path.join(current_path, file.name))
            blob.upload_from_file(file)
            blob.make_public()

        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error', 'message': 'No files found to upload'})


class CreateFolderForm(forms.Form):
    folder_name = forms.CharField(label='New Folder Name', max_length=100)

def convert_size(size_bytes):
    # Function to convert bytes to a human-readable format (KB, MB, GB)
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])

def list_files(request, path=''):
    bucket = storage.bucket()
    blobs = bucket.list_blobs(prefix=path)

    folders = set()
    files = []
    # Normalize the path to ensure it ends with a '/'
    if path and not path.endswith('/'):
        path += '/'

    if request.method == 'POST':
        form = CreateFolderForm(request.POST)

        if form.is_valid():
            print("THIS IS LIST FILES POST")
            folder_name = form.cleaned_data['folder_name']
            new_folder_path = os.path.join(path, folder_name) + '/'
            new_blob = bucket.blob(new_folder_path)
            new_blob.upload_from_string('')  # Create an empty blob to represent the folder
            # Redirect user to the newly created folder
            return redirect(reverse('list_files', kwargs={'path': new_folder_path}))
    else:
        form = CreateFolderForm()

    for blob in blobs:
        # Get the relative path to the blob from the given path
        relative_path = blob.name[len(path):]

        # Check if the relative path contains any slashes
        if '/' in relative_path:
            # It's a subdirectory or a file in a subdirectory
            # Extract the immediate subdirectory
            immediate_subdirectory = relative_path.split('/', 1)[0]
            folders.add(immediate_subdirectory.rstrip('/'))
        else:
            # It's a file in the current directory
            # Extract only the file name with extension
            file_name = os.path.basename(blob.name)
            if file_name:  # Check if the file name is not empty
                file_url = blob.public_url
                file_size = convert_size(blob.size)
                files.append((file_name, file_url, file_size))

    context = {
        'folders': sorted(folders),  # Sort folders for better readability
        'files': files,
        'current_path': path,
        'form': form,
    }

    return render(request, 'supplies/list_fir_files.html', context)


def delete_file(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        file_name = data.get('file_name')
        current_path = data.get('current_path')
        print("DELETE")
        print(current_path)
        print(file_name)
        blob = bucket.blob(os.path.join(current_path, file_name))
        blob.delete()
        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method or missing parameters'})



