from django.urls import path

from .views import (
    ConstructionObjectCreateView,
    ConstructionObjectDeleteView,
    ConstructionObjectDetailView,
    ConstructionObjectListView,
    ConstructionObjectUpdateView,
    WorkItemCreateView,
    WorkItemDeleteView,
    WorkItemDetailView,
    WorkItemListView,
    WorkItemUpdateView,
)

app_name = 'objects'

urlpatterns = [
    path('objects/', ConstructionObjectListView.as_view(), name='list'),
    path('objects/create/', ConstructionObjectCreateView.as_view(), name='create'),
    path('objects/<int:pk>/', ConstructionObjectDetailView.as_view(), name='detail'),
    path('objects/<int:pk>/edit/', ConstructionObjectUpdateView.as_view(), name='update'),
    path('objects/<int:pk>/delete/', ConstructionObjectDeleteView.as_view(), name='delete'),
    path('work-items/', WorkItemListView.as_view(), name='work-item-list'),
    path('work-items/create/', WorkItemCreateView.as_view(), name='work-item-create'),
    path('work-items/<int:pk>/', WorkItemDetailView.as_view(), name='work-item-detail'),
    path('work-items/<int:pk>/edit/', WorkItemUpdateView.as_view(), name='work-item-update'),
    path('work-items/<int:pk>/delete/', WorkItemDeleteView.as_view(), name='work-item-delete'),
]
