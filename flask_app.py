from flask import Flask, request, send_file
from flask import render_template

import PIL
from PIL import Image
from PIL import ImageFilter

import io
from StringIO import StringIO
import requests
import csv
import boto3

import re

app = Flask(__name__)
s3 = boto3.client('s3')

@app.route('/')
def index(name=None):
    return render_template('imageHome.html', name=name)

@app.route('/csvRead', methods=['GET', 'POST'])
def csvRead():
	if request.method == 'POST':
		imageList = []
		croppedImages = []
		imageCountList = [0]
		imageCount = 1

		file = request.files['pic']
		if not file:
			return "No file"

		stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
		csv_input = csv.reader(stream)

		rowCount = 0
		for row in csv_input:
			if rowCount > 0:
				if len(row[0]) > 0:
					editUpload(row[0], imageList, croppedImages, imageCountList, imageCount)
				else:
					imageList.append("No image")
					croppedImages.append("No image")
					imageCountList.append(imageCountList[-1]+1)
			rowCount += 1

		imageCountList.pop(0)
		columnValues = zip(imageList, croppedImages, imageCountList)

		return render_template("returnData.html", data=columnValues)


@app.route('/urlRead', methods=['GET', 'POST'])
def urlRead():
	if request.method == 'POST':
		text = request.form['enterUrl']
		imageList = []
		croppedImages = []
		imageCount = 0
		imageCountList = [0]
		editUpload(text, imageList, croppedImages, imageCountList, imageCount)

		columnValues = zip(imageList, croppedImages, imageCountList)

		return render_template("returnData.html", data=columnValues)


def editUpload (imageUrl, imageList, croppedImages, imageCountList, imageCount):
	try:
		response = requests.get(imageUrl, stream=True, headers={'User-Agent': 'Mozilla/5.0'}).raw
		imCrop = Image.open(response)
		imageFormat = imCrop.format

		if (imCrop.size[1] > imCrop.size[0]) or (imCrop.size[1] == imCrop.size[0]):
			newHeightTall = int((1080 / float(imCrop.size[0])) * float(imCrop.size[1]))
			crop = int((newHeightTall - 770)/2)
			imCrop = imCrop.resize((1080, newHeightTall))
			newIm = imCrop.crop((0,crop,1080,newHeightTall - crop))
		else:
			newWideWidth = int((770 / float(imCrop.size[1])) * float(imCrop.size[0]))
			crop = int((newWideWidth - 1080)/2)
			imCrop = imCrop.resize((newWideWidth, 770))
			newIm = imCrop.crop((crop,0,newWideWidth - crop,770))

		quality_val = 90
		tempImage = StringIO()
		if imageFormat == 'PNG':
			newIm.save(tempImage, 'png')
		else:
			newIm.save(tempImage, 'jpeg')

		filename = re.sub('[^a-zA-Z0-9 \n\.]', '', imageUrl.rsplit("/",1)[1]).replace(" ", "_").replace(".", "") + "." + imageFormat
		print filename
		bucket_name = 'stacker-images'
		s3.put_object(
			Body=tempImage.getvalue(),
			Bucket=bucket_name,
			Key='cropped'+filename,
			ACL='public-read'
		)
		fileUrl = 'https://s3.amazonaws.com/stacker-images/' + 'cropped' + filename
		print fileUrl
		croppedImages.append(fileUrl)

		response = requests.get(imageUrl, stream=True, headers={'User-Agent': 'Mozilla/5.0'}).raw

		im = Image.open(response)
		blurred = im.filter(ImageFilter.GaussianBlur(25))
		blurred = blurred.resize((1080, 770))

		if im.size[0] == im.size[1]:
			newWidth = 770
			newHeight = 770
			im = im.resize((newWidth,newHeight))
			offset = (int((blurred.size[0] - newWidth) // 2), 0)
		elif im.size[0] < im.size[1]:
			newWidth = (770 / float(im.size[1])) * float(im.size[0])
			newHeight = 770
			im = im.resize((int(newWidth),newHeight))
			offset = (int((blurred.size[0] - int(newWidth)) // 2), 0)
		else:
			newWidth = 1080
			newHeight = (1080 / float(im.size[0])) * float(im.size[1])
			im = im.resize((newWidth,int(newHeight)))
			offset = (0, int((blurred.size[1] - int(newHeight)) // 2))

		blurred.paste(im, offset)
		blurred1 = StringIO()
		if imageFormat == 'PNG':
			blurred.save(blurred1, 'png')
		else:
			blurred.save(blurred1, 'jpeg')

		filename = re.sub('[^a-zA-Z0-9 \n\.]', '', imageUrl.rsplit("/",1)[1]).replace(" ", "_").replace(".", "") + "." + imageFormat
		bucket_name = 'stacker-images'
		s3.put_object(
			Body=blurred1.getvalue(),
			Bucket=bucket_name,
			Key=filename,
			ACL='public-read'
		)
		fileUrl = 'https://s3.amazonaws.com/stacker-images/' + filename
		print fileUrl
		imageList.append(fileUrl)
		imageCountList.append(imageCountList[-1]+1)

	except:
		print 'Error - ' + imageUrl
		imageList.append(imageUrl)
		croppedImages.append(imageUrl)
		imageCountList.append(imageCountList[-1]+1)


@app.route('/hostImages', methods=['GET', 'POST'])
def hostImages():
	if request.method == 'POST':
		imageList = []

		uploadedFolder = request.files.getlist("imageFolder")
		print uploadedFolder
		if not file:
			return "No file"
		for uploadedFile in uploadedFolder:
			print uploadedFile.filename

			blurred1 = StringIO()
			uploadedFile.save(blurred1)
			bucket_name = 'stacker-images'
			fileKey = re.sub('[^a-zA-Z0-9 \n\.]', '', uploadedFile.filename).replace(" ", "_").replace("/", "_")
			s3.put_object(
				Body=blurred1.getvalue(),
				Bucket=bucket_name,
				Key=fileKey,
				ACL='public-read'
			)

			imageList.append('https://s3.amazonaws.com/stacker-images/' + fileKey)

		return render_template("returnHostedLinks.html", data=imageList)

