from diagrams import Cluster, Diagram
from diagrams.gcp.analytics import BigQuery, Dataflow, PubSub
from diagrams.gcp.compute import AppEngine, Functions
from diagrams.gcp.database import BigTable
from diagrams.programming import flowchart
from diagrams.gcp.iot import IotCore
from diagrams.gcp.storage import GCS

with Diagram("ContentRepo Page Structure", show=False):
 
  
    with Cluster("Pages"):
        pages = flowchart.Database()
        with Cluster("Homepage"):
            homepage = flowchart.MultipleDocuments()

        with Cluster("ContentPage Index"):
            content_page_index = flowchart.MultipleDocuments()

        with Cluster("ContentPage"):
            content_page = flowchart.MultipleDocuments()

    pages >> homepage >> content_page_index >> content_page

with Diagram("ContentPage Data Structure", show=False):
    

    with Cluster("ContentPage"):
        
        web = flowchart.Document()

            #with Cluster("Content Page Index"):
        whatsapp = flowchart.Document()

            #with Cluster("Content Page"):
        sms = flowchart.Document()
        ussd = flowchart.Document()
        messenger = flowchart.Document()
        viber = flowchart.Document()

   