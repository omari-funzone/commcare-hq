from django.conf.urls.defaults import *

urlpatterns = patterns('',    
        (r'^inspector/(?P<table_name>.*)/$', 'dbanalyzer.views.inspector'),
        (r'^showgraph/$', 'dbanalyzer.views.show_rawgraphs'),
        (r'^showgraph/(?P<graph_id>\d+)/$', 'dbanalyzer.views.view_rawgraph'),
        (r'^showgraph/all/$', 'dbanalyzer.views.show_multi'),
)
