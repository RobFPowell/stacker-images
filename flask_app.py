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

app = Flask(__name__)
s3 = boto3.client('s3')

@app.route('/')
def index(name=None):
    # return 'Hello, World!'
    return render_template('imageHome.html', name=name)

@app.route('/csvRead', methods=['GET', 'POST'])
def csvRead():
	# print "hello"
	if request.method == 'POST':
		imageList = []

		file = request.files['pic']
		if not file:
			return "No file"

		stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
		csv_input = csv.reader(stream)

		rowCount = 0
		for row in csv_input:
			if rowCount > 0:
				if len(row[3]) > 0:
					editUpload(row[3], imageList)
			rowCount += 1
		# print imageList
		return render_template("returnData.html", data=imageList)
		# print imageList
		# return ("<p>" + "</p><p>".join(imageList) + "</p>")


def editUpload (imageUrl, imageList):
	try:
		response = requests.get(imageUrl, stream=True).raw
		print 'requested image'
		im = Image.open(response)
		print 'Image loaded'

		blurred = im.filter(ImageFilter.GaussianBlur(25))
		blurred = blurred.resize((1080, 770))

		print "Blur worked"
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

		print newWidth, newHeight
		print offset
		blurred.paste(im, offset)

		blurred1 = StringIO()
		blurred.save(blurred1, 'jpeg')

		filename = imageUrl.rsplit("/",1)[1]
		bucket_name = 'stacker-images'
		# s3.put_object(
		# 	Body=blurred1.getvalue(),
		# 	Bucket=bucket_name,
		# 	Key=filename,
		# 	ACL='public-read'
		# )
		fileUrl = 'https://s3.amazonaws.com/stacker-images/' + filename
		print fileUrl
		imageList.append(fileUrl)
		# print imageList
		# print fileUrl
	except:
		print 'Error - ' + imageUrl
		imageList.append('Error - ' + imageUrl)
		# pass

# def uploadImage ():
# 	filename = 'Your_Highness_Poster.jpg'
# 	bucket_name = 'stacker-images'
# 	s3.upload_file(filename, bucket_name, filename, ExtraArgs={'ACL':'public-read'})
# 	fileUrl = 'https://s3.amazonaws.com/stacker-images/' + filename

