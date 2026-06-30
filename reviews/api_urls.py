from django.urls import path
from . import api_views

app_name = 'reviews_api'

urlpatterns = [
    path('kpi-summary/', api_views.kpi_summary_data, name='kpi_summary_data'),
    path('trend-chart/', api_views.trend_chart_data, name='trend_chart_data'),
    path('platform-chart/', api_views.platform_chart_data, name='platform_chart_data'),
    path('thematic-analysis/', api_views.thematic_analysis_data, name='thematic_analysis_data'),
    path('reviews-table/', api_views.reviews_table_data, name='reviews_table_data'),
    path('rating-distribution/', api_views.rating_distribution_data, name='rating_distribution_data'),
]
