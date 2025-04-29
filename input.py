import os
from config import *
from google.oauth2 import service_account
import sys
import importlib
importlib.reload(sys)
#sys.setdefaultencoding('utf8')
from google.cloud import vision
from google.cloud import storage
from google.protobuf import json_format
from doc_txt_detect import detect_hand_writtent_text
from doc_txt_detect import fixHandWrittenText
from doc_txt_detect import PDF
from fpdf import FPDF
import re

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Hospital Name', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 10, 'Address: 123 Hospital St, City, Country', 0, 1, 'C')
        self.cell(0, 10, 'Phone: +1234567890', 0, 1, 'C')
        self.ln(10)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

    def patient_info(self, data):
        self.set_font('Arial', '', 12)
        self.cell(0, 10, f"Name: {data['name']}", 0, 1)
        self.cell(0, 10, f"Age: {data['age_gender']['age']}", 0, 1)
        self.cell(0, 10, f"Gender: {data['age_gender']['gender']}", 0, 1)
        self.cell(0, 10, f"Weight: {data['weight']}", 0, 1)
        self.cell(0, 10, f"Phone: {data['additional_info']['ph_no']}", 0, 1)
        self.cell(0, 10, f"Date: {data['additional_info']['date']}", 0, 1)
        self.ln(10)

    def prescription_table(self, prescriptions):
        self.set_font('Arial', 'B', 12)
        self.cell(40, 10, 'Medicine', 1)
        self.cell(40, 10, 'Dosage', 1)
        self.cell(40, 10, 'Frequency', 1)
        self.cell(40, 10, 'Duration', 1)
        self.ln()
        self.set_font('Arial', '', 12)
        for item in prescriptions:
            self.cell(40, 10, item['medicine'], 1)
            self.cell(40, 10, item['dosage'], 1)
            self.cell(40, 10, item['frequency'], 1)
            self.cell(40, 10, item['duration'], 1)
            self.ln()

def create_prescription_pdf(data):
    pdf = PDF()
    pdf.add_page()
    pdf.chapter_title('Patient Information')
    pdf.patient_info(data)
    pdf.chapter_title('Clinical Description')
    pdf.chapter_body(data['clinical_description'])
    pdf.chapter_title('Prescription')
    pdf.prescription_table(data['prescriptions'])
    pdf.output('prescription.pdf')




credentials = service_account.Credentials.from_service_account_file(GCP_SERVICE_AUTH_FILE)

print("""
1.This model requires input in a folder.Please keep all the input file in single folder. 
2.Create a folder 001 under parent directory and store all test  data  inside the folder.
Example: 

|---data
|   ----001
|       ------ input1.pdf
|       ------ input2.pdf
|       ------ input3.pdf

3. Pass the parent folder name to python program



""")
# detect_hand_writtent_text('gs://ocr_optum_vision/input/1.pdf','gs://ocr_optum_vision/output/' , '/Users/msingh16/Desktop/OBM/Work/AI:ML Automation/OCR_VisionAPI/data/output/1.pdf')
  


input_dir=str(input("Please enter top level directory of the test data: "))

if os.path.isdir(input_dir):
    print("Input directory path is valid")
else:
    print("\n Entered path is not valid please check the format and enter again ")
    os._exit(1)

data_dir=os.path.abspath(input_dir)

if not os.path.isdir(os.path.abspath(data_dir)+"/001"):
    print("Could not find the input directory (001) in entered path. Please check the input path")
    os._exit(2)

if not os.path.exists(os.path.abspath(data_dir)+"/output/"):
        os.makedirs(os.path.abspath(data_dir)+"/output/")

filtered_content=""

for input_file in os.listdir(data_dir+"/001"):
    if input_file.__contains__("DS_Store"):
        continue
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.get_bucket("ocr_optum_vision")
    blob = bucket.blob("input/"+input_file)
    blob.upload_from_filename(os.path.abspath(data_dir)+"/001/"+input_file)
    gcs_source_uri = "gs://ocr_optum_vision/input/" +input_file
    gcs_destination_uri= "gs://ocr_optum_vision/output/" 
    filtered_content=detect_hand_writtent_text(gcs_source_uri,gcs_destination_uri , os.path.abspath(data_dir)+"/output/"+input_file)
    # Create an instance of the class
    # my_instance = PDF()

    # # Call the function
    # my_instance.create_prescription_pdf(data)


    # fixHandWrittenText(vision_api_response)
create_prescription_pdf(filtered_content)
print("All files are processed. Please find the output in data/output directory..")
print("Filtered content in main:", filtered_content)

#gcs_destination_uri="gs://mldata101/"
#gcs_source_uri="gs://mldata101/FORM-FREETEXTINOUTBOXES_4.pdf"
#async_detect_document(gcs_source_uri,gcs_destination_uri,"result.txt"




# create_prescription_pdf(data)
