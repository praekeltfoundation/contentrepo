from django.http import HttpResponseRedirect
from django.shortcuts import render
from .forms import UploadFileForm
from .utils import import_content


def upload_file(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            job = handle_uploaded_file(request.FILES["file"])
            if job == "success":
                return HttpResponseRedirect("/admin/")
            else:
                form.add_error("file", "Unsuccessful.")
    else:
        form = UploadFileForm()
    return render(request, "upload.html", {"form": form})


def handle_uploaded_file(f):
    import_content(f)
