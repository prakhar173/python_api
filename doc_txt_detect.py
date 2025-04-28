import json
from google.oauth2 import service_account
from google.protobuf.json_format import MessageToDict
from google.protobuf.json_format import Parse
from config import *
# encoding=utf8
import sys
import importlib
importlib.reload(sys)
# Import the required libraries.
import openai
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.identity import ClientSecretCredential
from fpdf import FPDF
import re
# set default encoding to utf-8

#sys.setdefaultencoding('utf8')
from google.cloud import vision
from google.cloud import storage
from google.protobuf import json_format
from google.protobuf.json_format import MessageToJson
from google.cloud.vision_v1.types import AnnotateFileResponse
credentials = service_account.Credentials.from_service_account_file(GCP_SERVICE_AUTH_FILE)

# Load environment variables from .env file
# load_dotenv()

# # # Define the Azure endpoint.
# azure_endpoint = os.getenv("AZURE_ENDPOINT")

# # Set up Azure credentials.
# az_cred = ClientSecretCredential(
#     tenant_id=os.getenv("TENANT_ID"),
#     client_id=os.getenv("CLIENT_ID"),
#     client_secret=os.getenv("CLIENT_SECRET")
# )

# # # Get the bearer token provider.
# token_provider = get_bearer_token_provider(az_cred, "https://cognitiveservices.azure.com/.default")

# # # Initialize the OpenAI client.
# oai_client = openai.AzureOpenAI(
#     azure_endpoint=azure_endpoint,
#     api_version="2024-06-01",
#     azure_deployment="gpt-4o_2024-05-13",
#     azure_ad_token_provider=token_provider,
#     default_headers={
#         "projectId": os.getenv("PROJECT_ID")
#     }
# )

def detect_hand_writtent_text(gcs_source_uri, gcs_destination_uri,input_file):
    """OCR with PDF/TIFF as source files on GCS"""

    print(dir(vision.AnnotateFileResponse))
    # Supported mime_types are: 'application/pdf' and 'image/tiff'
    mime_type = 'application/pdf'
    #mime_type = 'image/tiff'
   
    # How many pages should be grouped into each json output file.
    batch_size = 1
    client = vision.ImageAnnotatorClient(credentials=credentials)
    feature = vision.Feature(
        type=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)
    gcs_source = vision.GcsSource(uri=gcs_source_uri)
    print("Processing File "+input_file.split("/")[-1]+" ...")
    input_config = vision.InputConfig(
        gcs_source=gcs_source, mime_type=mime_type)
    gcs_destination = vision.GcsDestination(uri=gcs_destination_uri)
    output_config = vision.OutputConfig(
        gcs_destination=gcs_destination, batch_size=batch_size)
    async_request = vision.AsyncAnnotateFileRequest(
        features=[feature], input_config=input_config,
        output_config=output_config)
    operation = client.async_batch_annotate_files(
        requests=[async_request])

    print('Waiting for the operation to finish.')
    operation.result(timeout=180)

    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.get_bucket(BUCKET_NAME)
    # Process the first output from API
    blob=bucket.blob("output/output-1-to-1.json")
    #json_string = blob.download_as_bytes.download_as_string()
    json_string = blob.download_as_text()
    
    
    # Assuming json_string is a dictionary
    json_dict = json.loads(json_string)

    # Remove the extra field
    if '^' in json_dict:
     del json_dict['^']

    # Convert the dictionary back to a string
    json_string = json.dumps(json_dict)
    
    # Assuming json_string is a JSON string
    data = json.loads(json_string)

    # Access the responses
    responses12 = data.get('responses', [])
    
    #test this code
    prefix = 'output/out'

    blob_list = list(bucket.list_blobs(prefix=prefix))
    print('Output files:')
    for blob in blob_list:
        print(blob.name)
        
    output = blob_list[0].download_as_text()

    #json_string = output.download_as_string()
   
    #test this code
    
    # Parse the JSON string
    #response = Parse(responses12, vision.AnnotateFileResponse())
     # # Assuming `response` is a ChatCompletion object

    # # Parse the JSON response
    json_object = json.loads(output)
    print("JSON object",json_object)
    load_dotenv()
    azure_endpoint = os.getenv("AZURE_ENDPOINT")

    # Set up Azure credentials.
    az_cred = ClientSecretCredential(
        tenant_id=os.getenv("TENANT_ID"),
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET")
    )

    # # Get the bearer token provider.
    token_provider = get_bearer_token_provider(az_cred, "https://cognitiveservices.azure.com/.default")

    # # Initialize the OpenAI client.
    oai_client = openai.AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_version="2024-06-01",
        azure_deployment="gpt-4o_2024-05-13",
        azure_ad_token_provider=token_provider,
        default_headers={
            "projectId": os.getenv("PROJECT_ID")
        }
    )
    messages = [{"role": "system", "content": "Hi, you are an intelligent Medical Pharmacist and you have been given an output of handwritten prescription using vision api , please filter out the content if possible , please only provide the data in key value pair in json format , just share only the json object don't add json and backticks in response ,also use the following format to create payload {'name': 'ASHVIKA', 'age_gender': {'age': '4', 'gender': 'F'}, 'clinical_description': 'URTI', 'weight': '13.25 kg', 'prescriptions': [{'medicine': 'CALPOL', 'dosage': '4ML', 'frequency': 'Q6H', 'duration': '3d'}, {'medicine': 'DELCON', 'dosage': '3 mL', 'frequency': 'TDS', 'duration': '3d'}, {'medicine': 'LEVOLIN', 'dosage': '3 mL', 'frequency': 'TDS', 'duration': '5d'}, {'medicine': 'MEFTAL-P', 'dosage': '3 mL', 'frequency': 'TDS', 'duration': '5d'}], 'additional_info': {'ph_no': '8086993168', 'date': '20-9-2022'}}"} , {"role": "user", "content":output}]
    # Request the model to process the messages.
    response = oai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )

    # # Assuming `response` is a ChatCompletion object
    response_json = response.model_dump_json(indent=2)

    # # Parse the JSON response
    response_dict = json.loads(response_json)

    # # Access the content
    json_content=response_dict['choices'][0]['message']['content']

    filtered_content = re.sub(r'json|', '', json_content).strip()
    print("Filtered content:", filtered_content)

    data = json.loads(filtered_content)
    print("Filtered content:", data)
    return data

 


#  Define the messages to be processed by the model.
# # messages = [{"role": "user", "content": "Hi, what is most famous in Rome"}]
def fixHandWrittenText(vision_api_response):
    # # Define the Azure endpoint.
    load_dotenv()
    azure_endpoint = os.getenv("AZURE_ENDPOINT")

    # Set up Azure credentials.
    az_cred = ClientSecretCredential(
        tenant_id=os.getenv("TENANT_ID"),
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET")
    )

    # # Get the bearer token provider.
    token_provider = get_bearer_token_provider(az_cred, "https://cognitiveservices.azure.com/.default")

    # # Initialize the OpenAI client.
    oai_client = openai.AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_version="2024-06-01",
        azure_deployment="gpt-4o_2024-05-13",
        azure_ad_token_provider=token_provider,
        default_headers={
            "projectId": os.getenv("PROJECT_ID")
        }
    )
    messages = [{"role": "system", "content": "Hi, you are an intelligent Medical Pharmacist and you have been given an output of handwritten prescription using vision api , please filter out the content if possible , please only provide the data in key value pair in json format , just share only the json object don't add json and backticks in response ,also use the following format to create payload {'name': 'ASHVIKA', 'age_gender': {'age': '4', 'gender': 'F'}, 'clinical_description': 'URTI', 'weight': '13.25 kg', 'prescriptions': [{'medicine': 'CALPOL', 'dosage': '4ML', 'frequency': 'Q6H', 'duration': '3d'}, {'medicine': 'DELCON', 'dosage': '3 mL', 'frequency': 'TDS', 'duration': '3d'}, {'medicine': 'LEVOLIN', 'dosage': '3 mL', 'frequency': 'TDS', 'duration': '5d'}, {'medicine': 'MEFTAL-P', 'dosage': '3 mL', 'frequency': 'TDS', 'duration': '5d'}], 'additional_info': {'ph_no': '8086993168', 'date': '20-9-2022'}}"} , {"role": "user", "content":vision_api_response}]
    # Request the model to process the messages.
    response = oai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )

    # # Assuming `response` is a ChatCompletion object
    response_json = response.model_dump_json(indent=2)

    # # Parse the JSON response
    response_dict = json.loads(response_json)

    # # Access the content
    json_content=response_dict['choices'][0]['message']['content']
    
    filtered_content = re.sub(r'json|', '', json_content).strip()
    data = json.loads(filtered_content)
    print("Filtered content:", filtered_content)
    # create_prescription_pdf(data)
    return filtered_content


# print(data)

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Prescription Details', 0, 1, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

def create_prescription_pdf(data):
    pdf = PDF()
    pdf.add_page()

    # Add Patient Information
    pdf.chapter_title('Patient Information')
    pdf.chapter_body(f"Name: {data['name']}")
    pdf.chapter_body(f"Age: {data['age_gender']['age']}")
    pdf.chapter_body(f"Gender: {data['age_gender']['gender']}")
    pdf.chapter_body(f"Weight: {data['weight']}")
    pdf.chapter_body(f"Phone: {data['additional_info']['ph_no']}")
    pdf.chapter_body(f"Date: {data['additional_info']['date']}")

    # Add Clinical Description
    pdf.chapter_title('Clinical Description')
    pdf.chapter_body(data['clinical_description'])

    # Add Prescription
    pdf.chapter_title('Prescription')
    for item in data['prescriptions']:
        pdf.chapter_body(f"Medicine: {item['medicine']}")
        pdf.chapter_body(f"Dosage: {item['dosage']}")
        pdf.chapter_body(f"Frequency: {item['frequency']}")
        pdf.chapter_body(f"Duration: {item['duration']}")
        pdf.ln(5)

    pdf.output('prescription.pdf')


# create_prescription_pdf(data)
     




#gcs_destination_uri="gs://mldata101/"
#gcs_source_uri="gs://mldata101/FORM-FREETEXTINOUTBOXES_4.pdf"
#async_detect_document(gcs_source_uri,gcs_destination_uri,"result.txt")
