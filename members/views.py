from django.shortcuts import render
from django.http import HttpResponse ,  JsonResponse
import zipfile
import os
import shutil
import numpy as np 
import cv2
from django.middleware.csrf import get_token
from django.template import Template, Context
from pathlib import Path
import os
from django.shortcuts import render
from django.conf import settings
import os
import zipfile
import io
import shutil
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from zipupload.settings import MEDIA_ROOT
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

def members(request):
    return render(request, 'upload_zip.html')





def are_images_same(img1, img2, threshold=0.8):

    orb = cv2.ORB_create()
    keypoints1, descriptors1 = orb.detectAndCompute(img1, None)
    keypoints2, descriptors2 = orb.detectAndCompute(img2, None)

 
    if not keypoints1 or not keypoints2:
        return False


    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(descriptors1, descriptors2)


    matches = sorted(matches, key=lambda x: x.distance)

    good_matches = [match for match in matches if match.distance < threshold * min(len(keypoints1), len(keypoints2))]
    

    return len(good_matches) / min(len(keypoints1), len(keypoints2)) > threshold



def compare_images_in_zip(zip_file, destination_folder, threshold=0.8):
    matched_image_names = []

    all_files_destination = []
    for root, dirs, files in os.walk(destination_folder):
        for file in files:
            all_files_destination.append(os.path.join(root, file))

    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_file_images = zip_ref.namelist()

        for zip_image_name in zip_file_images:
            zip_image_data = zip_ref.read(zip_image_name)
            zip_image_array = np.frombuffer(zip_image_data, np.uint8)

            try:
                zip_image = cv2.imdecode(zip_image_array, cv2.IMREAD_GRAYSCALE)
            except cv2.error as e:
                print(f"Error decoding image {zip_image_name}: {str(e)}")
                continue

            for dest_image_path in all_files_destination:
                dest_image = cv2.imread(dest_image_path, cv2.IMREAD_GRAYSCALE)

                try:
                    if are_images_same(zip_image, dest_image, threshold):
                        matched_image_names.append((zip_image_name, os.path.basename(dest_image_path)))
                except cv2.error as e:
                    print(f"Error comparing images {zip_image_name} and {os.path.basename(dest_image_path)}: {str(e)}")
                    continue

    return matched_image_names



def upload_zip(request):
    if request.method == 'POST':
        # Extracting the uploaded zip file
        uploaded_file = request.FILES['zip_file']
        project_path = os.path.dirname(os.path.abspath(__file__))

        django_app_folder = os.path.join(project_path, 'my_django_app')

        destination_folder = os.path.join(BASE_DIR, 'media\extracted_folder')



        with open('temp.zip', 'wb') as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)

        result = compare_images_in_zip('temp.zip', destination_folder)

        print(result,'###########################')

        image_data = [{'folder_path': destination_folder, 'image_name': os.path.basename(dest),'image_': os.path.basename(_)} for _, dest in result]




        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Matched Images</title>
        </head>
        <body>

        <h2>Matched Images</h2>

        {% for image in image_data %}
            <div>
                <p>Folder Path: {{ image.folder_path }}</p>
                <p>Image Name: {{ image.image_name }}</p>
                <img src="/media/extracted_folder/{{ image.image_name }}" alt="Matched Image" height="200px" width="200px">
                <img src="/media/extracted_folder/{{ image.image_name }}" alt="Matched Image" height="200px" width="200px">
            </div>
        {% endfor %}

        </body>
        </html>
        """

        html_content = Template(html_template).render(Context({'image_data': image_data}))

        return HttpResponse(html_content)

    csrf_token = get_token(request)

    original_html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upload Zip</title>
    </head>
    <body>

    <h2>Upload Zip</h2>

    <form method="post" enctype="multipart/form-data">
        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
        <input type="file" name="zip_file" accept=".zip" required>
        <button type="submit">Upload</button>
    </form>

    </body>
    </html>
    """
    
    return HttpResponse(original_html_content)



def compare_images(request):
    duplicate_images = None
    if request.method == 'POST' and request.FILES.get('zip_file'):
        
        uploaded_file = request.FILES['zip_file']

        
        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            zip_data = {name: zip_ref.read(name) for name in file_list}

        
        duplicate_images = find_duplicate_images(zip_data, MEDIA_ROOT)


        return render(request, 'compare_images.html', {'duplicate_images': duplicate_images})

    return render(request, 'compare_images.html')

def find_duplicate_images(zip_data, directory):
    duplicate_images = []

    
    for root, dirs, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)

            
            for zip_filename, zip_file_content in zip_data.items():
                if compare_images_opencv(zip_file_content, path):
                    duplicate_images.append((zip_filename, path))

    return duplicate_images

def compare_images_opencv(zip_image_content, existing_image_path):
    
    existing_image = cv2.imread(existing_image_path)

    
    if existing_image is None:
        return False  

    try:
        
        zip_image = cv2.imdecode(np.frombuffer(zip_image_content, np.uint8), -1)
    except cv2.error as e:
        print(f"Error decoding image: {e}")
        return False

   
    if zip_image is not None and zip_image.size != 0:
        
        if existing_image.shape == zip_image.shape:
            difference = cv2.subtract(existing_image, zip_image)
            b, g, r = cv2.split(difference)
            if cv2.countNonZero(b) == 0 and cv2.countNonZero(g) == 0 and cv2.countNonZero(r) == 0:
                return True  

    return False

def process_selected_duplicates(request):
    if request.method == 'POST':
        selected_images = request.POST.getlist('selected_images[]')
        print("Selected Images:", selected_images)
        return JsonResponse({'status': selected_images})

    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})