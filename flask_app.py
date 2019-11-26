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
from bs4 import BeautifulSoup
import string
import random

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
		imageSizes = []
		imageClasses = []

		file = request.files['pic']
		if not file:
			return "No file"

		stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
		csv_input = csv.reader(stream)

		rowCount = 0
		for row in csv_input:
			if rowCount > 0:
				if len(row) > 0:
					if len(row[0]) > 0:
						editUpload(row[0], imageList, croppedImages, imageCountList, imageCount, imageSizes, imageClasses)
					else:
						imageList.append("No image")
						croppedImages.append("No image")
						imageCountList.append(imageCountList[-1]+1)
						imageSizes.append('No image')
						imageClasses.append('flagImage')
				else:
					imageList.append("No image")
					croppedImages.append("No image")
					imageCountList.append(imageCountList[-1]+1)
					imageSizes.append('No image')
					imageClasses.append('flagImage')

			rowCount += 1

		imageCountList.pop(0)
		columnValues = zip(imageList, croppedImages, imageCountList, imageSizes, imageClasses)

		return render_template("returnData.html", data=columnValues)


@app.route('/urlRead', methods=['GET', 'POST'])
def urlRead():
	if request.method == 'POST':
		text = request.form['enterUrl']
		imageList = []
		croppedImages = []
		imageCount = 0
		imageCountList = [0]
		imageSizes = []
		imageClasses = []
		editUpload(text, imageList, croppedImages, imageCountList, imageCount, imageSizes, imageClasses)

		columnValues = zip(imageList, croppedImages, imageCountList, imageSizes, imageClasses)

		return render_template("returnData.html", data=columnValues)


def editUpload (imageUrl, imageList, croppedImages, imageCountList, imageCount, imageSizes, imageClasses):
	try:
		response = requests.get(imageUrl, stream=True, headers={'User-Agent': 'Mozilla/5.0'}).raw
		imCrop = Image.open(response)
		imageFormat = imCrop.format
		imageSize = str(imCrop.size[0]) + " x " + str(imCrop.size[1])
		if (imCrop.size[0] < 1080 or imCrop.size[1] < 770):
			imageClass = 'flagImage'
		else:
			imageClass = ''

		if (800 > imCrop.size[0]) or (570 > imCrop.size[1]):
			newIm = imCrop.filter(ImageFilter.GaussianBlur(200))
			newIm = newIm.resize((800, 570))
			offset = (int((newIm.size[0] - imCrop.size[0]) // 2), int((newIm.size[1] - imCrop.size[1]) // 2))
			newIm.paste(imCrop, offset)
		# crop to max dimensions, no resizing
		# elif (4000 < imCrop.size[0]) and (2857 < imCrop.size[1]):
		# 	newIm = imCrop.crop((int((imCrop.size[0] - 3997) // 2), int((imCrop.size[1] - 2850) // 2), imCrop.size[0] - int((imCrop.size[0] - 3997) // 2), imCrop.size[1] - int((imCrop.size[1] - 2850) // 2)))
		elif (4000 < imCrop.size[0]) and (2857 < imCrop.size[1]):
			if (imCrop.size[1] > imCrop.size[0]) or (imCrop.size[1] == imCrop.size[0]) or ((imCrop.size[1] * (1080.0 / 770.0)) > imCrop.size[0]):
				newHeightTall = int((3997 / float(imCrop.size[0])) * float(imCrop.size[1]))
				crop = int((newHeightTall - 2850)/2)
				imCrop = imCrop.resize((3997, newHeightTall))
				newIm = imCrop.crop((0,crop,3997,newHeightTall - crop))
			else:
				newWideWidth = int((2850 / float(imCrop.size[1])) * float(imCrop.size[0]))
				crop = int((newWideWidth - 3997)/2)
				imCrop = imCrop.resize((newWideWidth, 2850))
				newIm = imCrop.crop((crop,0,newWideWidth - crop,2850))
		elif (imCrop.size[1] > imCrop.size[0]) or (imCrop.size[1] == imCrop.size[0]) or ((imCrop.size[1] * (1080.0 / 770.0)) > imCrop.size[0]):
			newHeightTall = int(float(imCrop.size[0]) * float(770.0 / 1080.0))
			crop = int((imCrop.size[1] - newHeightTall) / 2)
			newIm = imCrop.crop((0,crop,imCrop.size[0],imCrop.size[1] - crop))
		else:
			newWideWidth = int(float(imCrop.size[1]) * float(1080.0 / 770.0))
			crop = int((imCrop.size[0] - newWideWidth) / 2)
			newIm = imCrop.crop((crop,0,imCrop.size[0] - crop,imCrop.size[1]))

		print newIm.size[0], newIm.size[1]
		quality = 95
		tempImage = StringIO()
		if imageFormat == 'PNG':
			newIm.save(tempImage, 'png', quality=quality)
		else:
			newIm.save(tempImage, 'jpeg', quality=quality)

		filename = re.sub('[^a-zA-Z0-9 \n\.]', '', imageUrl.rsplit("/",1)[1]).replace(" ", "_").replace(".", "") + "." + imageFormat
		print filename
		bucket_name = 'stacker-images'
		s3.put_object(
			Body=tempImage.getvalue(),
			Bucket=bucket_name,
			Key='cropped'+filename,
			ACL='public-read',
			ContentType='image'
		)
		fileUrl = 'https://s3.amazonaws.com/stacker-images/' + 'cropped' + filename
		print fileUrl
		croppedImages.append(fileUrl)

		response = requests.get(imageUrl, stream=True, headers={'User-Agent': 'Mozilla/5.0'}).raw

		im = Image.open(response)
		blurred = im.filter(ImageFilter.GaussianBlur(200))

		if (800 > im.size[0]) or (570 > im.size[1]):
			blurred = blurred.resize((800, 570))
			offset = (int((blurred.size[0] - im.size[0]) // 2), int((blurred.size[1] - im.size[1]) // 2))
		elif (4000 < im.size[0]) or (2857 < im.size[1]):
			blurred = blurred.resize((3997,2850))
			if im.size[0] == im.size[1]:
				newWidth = 2850
				newHeight = 2850
				im = im.resize((newWidth,newHeight))
				offset = (int((blurred.size[0] - newWidth) // 2), 0)
			elif im.size[0] < im.size[1]:
				newWidth = (2850 / float(im.size[1])) * float(im.size[0])
				newHeight = 2850
				im = im.resize((int(newWidth),newHeight))
				offset = (int((blurred.size[0] - int(newWidth)) // 2), 0)
			else:
				newWidth = 3997
				newHeight = (3997 / float(im.size[0])) * float(im.size[1])
				im = im.resize((newWidth,int(newHeight)))
				offset = (0, int((blurred.size[1] - int(newHeight)) // 2))
		elif (im.size[1] > im.size[0]) or (im.size[1] == im.size[0]) or ((im.size[1] * (1080.0 / 770.0)) > im.size[0]): #https://upload.wikimedia.org/wikipedia/commons/8/82/Casey_Farm_Rhode_Island.jpg
			blurred = blurred.resize((int(im.size[1] * float(1080.0 / 770.0)), im.size[1]))
			offset = (int((blurred.size[0] - im.size[0]) // 2), 0)
		else:
			blurred = blurred.resize((im.size[0], int(im.size[0] / float(1080.0 / 770.0))))
			offset = (0, int((blurred.size[1] - im.size[1]) // 2))

		blurred.paste(im, offset)
		blurred1 = StringIO()
		print blurred.size[0], blurred.size[1]
		if imageFormat == 'PNG':
			blurred.save(blurred1, 'png', quality=quality)
		else:
			blurred.save(blurred1, 'jpeg', quality=quality)

		filename = re.sub('[^a-zA-Z0-9 \n\.]', '', imageUrl.rsplit("/",1)[1]).replace(" ", "_").replace(".", "") + "." + imageFormat
		bucket_name = 'stacker-images'
		s3.put_object(
			Body=blurred1.getvalue(),
			Bucket=bucket_name,
			Key='edited' + filename,
			ACL='public-read',
			ContentType='image'
		)
		fileUrl = 'https://s3.amazonaws.com/stacker-images/' + 'edited' + filename
		print fileUrl
		imageList.append(fileUrl)
		imageCountList.append(imageCountList[-1]+1)
		imageSizes.append(imageSize)
		imageClasses.append(imageClass)

	except:
		print 'Error - ' + imageUrl
		imageList.append(imageUrl)
		croppedImages.append(imageUrl)
		imageCountList.append(imageCountList[-1]+1)
		imageClasses.append('flagImage')
		try:
			imageSizes.append(imageSize)
		except:
			imageSizes.append("Not available")

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
			fileExtension = fileKey.split(".")[1]
			randomString = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))
			fileKeyRandom = re.sub('[^a-zA-Z0-9 \n\.]', '', fileKey.split(".")[0] + randomString + "." + fileExtension)

			s3.put_object(
				Body=blurred1.getvalue(),
				Bucket=bucket_name,
				Key=fileKeyRandom,
				ACL='public-read',
				ContentType='image'
			)

			imageList.append('https://s3.amazonaws.com/stacker-images/' + fileKeyRandom)

		return render_template("returnHostedLinks.html", data=imageList)


@app.route('/storyPreview', methods=['GET', 'POST'])
def storyPreview():
	if request.method == 'POST':
		storyUrl = request.form['enterUrl']
		# storyUrl = 'https://thestacker.com/stories/1771/polar-bears-and-50-other-species-threatened-climate-change#11'
		slideNumber = int(storyUrl.split('#')[1]) - 1

		r = requests.get(storyUrl, headers={'User-Agent': 'Mozilla/5.0'})
		storySoup = BeautifulSoup(r.text)

		storyName = storySoup.find('h1').text.strip()

		slideArea = storySoup.find('div', class_="slide--"+ str(slideNumber))
		imageAttribution = slideArea.find('div', class_='views-field-field-image-attribution').text
		slideTitle = slideArea.find('div', class_='views-field-field-slide-caption').text
		slideBody = str(slideArea.find('div', class_='views-field-field-slide-description').contents[0]).decode('utf-8')
		slideImage = slideArea.find('img')['src']

		previewHTML = '<div class="card" style="width:300px;height:450px;overflow:scroll;margin:10px;margin-bottom:0px;padding:0px;box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);transition: 0.3s;border-radius: 5px;position: relative;"> <img class="card-image slideImage" src="https://thestacker.com' + slideImage + '" style="height: 215px;border-radius: 5px 5px 0 0;"> <div class="card-title-box" style="background: #15133F;color: white;width: 100%;height: 45px;opacity: 0.7;position: absolute;top: 170px;"><div class="card-title" style="padding-left: 10px;padding-right: 10px;font-size: 14px;line-height: 1.4;opacity: 1;text-align: center;font-weight: bold;">' + storyName + '</div></div><div class="slideContent" style="padding: 0px;margin: 0px;padding: 10px;padding-top: 5px;padding-bottom: 0px;font-size: 14px;color: black;text-align: left;opacity: 1;line-height: 1.5;"><div class="slideTitle" style="font-weight:bold;padding-bottom: 0px;">' + slideTitle + ' </div>' + slideBody + ' <div style="position:relative;bottom:0px;text-align:center;padding:0px;height:30px;background-color:white"><hr class="readLinkLine" style="padding:0px"><a class="readLink" href="' + storyUrl + '" style="color: #144899;text-decoration: none;padding: 0px;padding-bottom: 10px;font-size: 15px;font-weight: bold;">Read at Stacker</a></div> </div>'

		return render_template("storyPreview.html", data=previewHTML)

