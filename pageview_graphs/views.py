import json
from django.shortcuts import render
from home.models import PageView
from django.db.models import Count, F
from django.db.models.functions import TruncMonth


def page_views(request):
    page_view_data = json.dumps(get_views_data(), indent=4, sort_keys=True, default=str)
    return render(
        request, "page_views/page_views.html", {"page_view_data": page_view_data}
    )


def get_views_data():
    view_per_month = list(
        PageView.objects.annotate(month=TruncMonth("timestamp"))
        .values("month")
        .annotate(x=F("month"), y=Count("id"))
        .values("x", "y")
    )
    labels = [item["x"].date() for item in view_per_month]
    return {"data": view_per_month, "labels": labels}
