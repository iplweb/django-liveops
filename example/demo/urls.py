from django.urls import path

from demo.views import CreateDemoView, DemoIndexView, DemoListView, DoneView

app_name = "demo"

urlpatterns = [
    path("", DemoIndexView.as_view(), name="index"),
    path("operations/", DemoListView.as_view(), name="list"),
    path("new/<slug:kind>/", CreateDemoView.as_view(), name="new"),
    path("done/", DoneView.as_view(), name="done"),
]
