from flask import Flask, request, send_file, Response
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
import mammoth
from iptcinfo import IPTCInfo
from pyvirtualdisplay import Display
from selenium import webdriver
import time

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

@app.route('/imageData', methods=['GET','POST'])
def imageData():
    r = requests.get('https://thestacker.com/api/v1/slideshow/' + '3929', headers={'User-Agent': 'Mozilla/5.0'})
    storySoup = BeautifulSoup(r.text)
    allSlides = storySoup.find_all('media:content')
    print allSlides[0]['url']
    slideCount = 0
    for slide in allSlides:
        imageUrl = slide['url']
        response = requests.get(imageUrl, stream=True, headers={'User-Agent': 'Mozilla/5.0'}).raw
        im = response
        #print im.size
        info = IPTCInfo(im)
        slideTitle = slide.find('media:title').text
        info['title'] = slideTitle
        slideBody = str(slide.find('media:text').contents).replace(", u'\\n', ","").replace("\\r\\n\\r\\n', ","")
        info['description'] = slideBody
        info.save()
        #return Response(im,mimetype='image')
        slideCount += 1
        return Response(
            response,
            mimetype="image",
            headers={"Content-disposition": "attachment; filename=" + slideCount + ".jpg"})

@app.route('/storyHTML', methods=['GET', 'POST'])
def storyHTML():
	if request.method == 'POST':
		storyID = request.form['enterID']
		select = request.form.get('noImages')
		print select
		if select == "No images":
			r = requests.get('https://thestacker.com/api/v1/slideshow/' + storyID, headers={'User-Agent': 'Mozilla/5.0'})
			storySoup = BeautifulSoup(r.text)
                        allSlides = storySoup.find_all('media:content')
			storyOutput = ""
			print allSlides[1].find('media:title')
			for slide in allSlides:
				slideTitle = slide.find('media:title').text
				slideBody = str(slide.find('media:text').contents).replace(", u'\\n', ","").replace("\\r\\n\\r\\n', ","").replace("', <br/>, u'\\r\\n","<br/>").replace(", u'\\r\\n]]>']","").replace("[u'","").replace('[u"',"").replace('\\r\\n\\r\\n",',"")
				storyOutput = storyOutput + "<h2>" + slideTitle + "</h2>" + slideBody
                        storyName = allSlides[0].find('media:title').text
			storyLink = str(storySoup.find('link'))
			storyLink = storySoup.find('dcterms:modified').nextSibling.nextSibling
			print storyLink
			storyAuthor = storySoup.find('author').text
			storyOutput = "<p>Story name: " + allSlides[0].find('media:title').text + "<br>Story link: " + storyLink + "<br>Author: " + storyAuthor + "</p>" + storyOutput
		else:
	    	        # Scrape main feed with images
                        #r = requests.get('https://thestacker.com/api/v1/slideshow/' + storyID, headers={'User-Agent': 'Mozilla/5.0'})
                        #storySoup = BeautifulSoup(r.text)
                        #allSlides = storySoup.find_all('media:content')
                        #storyName = allSlides[0].find('media:title').text
                        #storyLink = storySoup.find('dcterms:modified').nextSibling.nextSibling
                        #storyAuthor = storySoup.find('author').text
                        #storyOutput = ""
                        #for slide in allSlides:
                        #    slideTitle = slide.find('media:title').text
                        #    slideImage = slide['url']
                        #    slideAttribution = slide.find('media:credit').text
                        #    slideBody = str(slide.find('media:text').contents).replace(", u'\\n', ","").replace("\\r\\n","").replace("\\u2018","").replace("\\u2019","").replace("\\xa0"," ").replace("\\u2014", "-").replace("\\u201c",'"').replace("\\u201d",'"').replace("[u'\\n'","").replace(", u']]>']","").replace("\\xe9","e").replace("\\xf6","o").replace("]]>","")
                        #    storyOutput = storyOutput + "<br><img src='" + slideImage + "'>" + "<h5>" + slideAttribution + "</h5>" + "<h2>" + slideTitle + "</h2>" + slideBody
                        #storyOutput = "<p>Story name: " + allSlides[0].find('media:title').text + "<br>Story link: " + storyLink + "<br>Author: " + storyAuthor + "</p>" + storyOutput

                        #Scrape single page feed with images
                        r = requests.get('https://thestacker.com/api/v1/slideshow/' + storyID + '?_format=single_item_xml', headers={'User-Agent': 'Mozilla/5.0'})
			storySoup = BeautifulSoup(r.text)
			storyName = storySoup.find('item').find('title').text.encode('utf-8')
			storyLink = storySoup.find('dcterms:modified').nextSibling.nextSibling.nextSibling
                        storyContent = str(storySoup.find('content:encoded').contents).encode('ascii', 'ignore')
                        #storyContent = unicode(storySoup.find('content:encoded').contents).replace(", u'\\n', ","").replace("\\r\\n","").replace("\\u2018","").replace("\\u2019","").replace("\\xa0"," ").replace("\\u2014", "-").replace("\\u201c",'"').replace("\\u201d",'"').replace("[u'\\n'","").replace(", u']]>']","").replace("\\xe9","e").replace("\\xf6","o")
			storyAuthor = storySoup.find('author').text
                        storyLeadImage = storySoup.find('media:content')['url'].rsplit('/',1)
                        storyLeadImage = "https://thestacker.com/sites/default/files/" + storyLeadImage[1]
                        storyOutput = "<p>Story name: "+storyName+"<br>Story link: "+storyLink+"<br>Author: "+storyAuthor+"</p>"+ "<img src='" + storyLeadImage +"'>"+storyContent

		# with open('test.txt', "w") as test:
		# 	test.write(storyOutput.encode('utf-8'))
		return render_template("storyHTML.html", data=storyOutput, storyID=storyID, storyName=storyName, storyLink=storyLink, storyAuthor=storyAuthor)

@app.route('/getStory')
def getStory(name=None):
    return render_template('getStory.html', name=name)

@app.route('/getTextFile', methods=['GET', 'POST'])
def getTextFile(name=None):
    storyText = request.form['textFileContent']
    storyID = request.form['storyID']
    return Response(
        storyText,
        mimetype="text",
        headers={"Content-disposition": "attachment; filename=" + storyID + ".txt"})

@app.route('/wordToHTML', methods=['POST'])
def wordToHTML():
    wordDoc = request.files['wordDoc']
    mammothIt = mammoth.convert_to_html(wordDoc)
    replaceHTML = mammothIt.value.replace('</p><p>-','<br>-').replace('</p><p>---','<br>---').replace('<p>(---','(---').replace('---)</p>','---)').replace('---)<br>','---)<p>').replace('&quot;','"').replace('&amp;','&')
    splitSlides = replaceHTML.split('(---')
    slideTable = []
    for slide in splitSlides:
        slideTable.append(slide[slide.find('---)')+4:])
    slideTitles = slideTable[1::2]
    slideBody = slideTable[2::2]
    storyTable = zip(slideTitles, slideBody)
    return render_template("storyPreview.html", data=replaceHTML, storyTable=storyTable)
    return Response(
        mammothIt.value.replace('</p><p>-','<br>-').replace('</p><p>---','<br>---').replace('<p>(---','(---').replace('---)</p>','---)').replace('---)<br>','---)<p>').replace('&amp;','&'),
        mimetype="text",
        headers={"Content-disposition": "attachment; filename=story.txt"})

@app.route('/linkChecker', methods=['POST'])
def linkChecker():
    if request.method == 'POST':
        storyId = request.form['enterIDLink'].split(',')[0]
        partnerName = request.form['enterIDLink'].split(',')[1].strip()
        wordRequest = BeautifulSoup(requests.get('https://docs.google.com/spreadsheets/d/e/2PACX-1vRylbIXrAv6MvlqnheFdGx64jLuno90gH4GJkszDB5_cwZJsV-9lFj76BbXi3LbYwoCY4OyyYCTVbVQ/pubhtml?gid=0&single=true').text)
        wordRows = wordRequest.find_all('tr')

        noNoWords = []

        for wordRow in wordRows:
            try:
                if partnerName == wordRow.find_all('td')[1].text:
                    noNoWords.append(str(wordRow.find_all('td')[0].text))
            except:
                pass

        slideList = []
        slideBodyList = []
        linkList = []

        r = requests.get('https://stacker.com/api/v1/slideshow/' + str(storyId), headers={'User-Agent': 'Mozilla/5.0'})
        feedSoup = BeautifulSoup(r.text)
        allStories = feedSoup.find_all('item')
        for storySoup in allStories:
            allSlides = storySoup.find_all('media:content')
            try:
                storyName = storySoup.find('media:content').find('media:title').text.encode("utf8")
            except:
                storyName = 'Error'

            slideCount = 0
            for slide in allSlides:
                slideTitle = slide.find('media:title').text.replace(", u'\\n', ","").replace("\\r\\n","").replace("\\u2018","").replace("\\u2019","").replace("\\xa0"," ").replace("\\u2014", "-").replace("\\u201c",'"').replace("\\u201d",'"').replace("[u'\\n'","").replace(", u']]>']","").replace("\\xe9","e").replace("\\xf6","o").encode("utf8")
                slideBody = str(slide.find('media:text').contents).encode("utf8")
                for word in noNoWords:
                    if word in slideBody:
                    #print storyName, "|", slideCount, "|", word, "|", slideBody
                        slideList.append(slideTitle)
                        slideBodyList.append(slideBody)
                        linkList.append(word)

                slideCount = slideCount + 1
            columnValues = zip(slideList,linkList,slideBodyList)
            return render_template("returnLinks.html", data=columnValues)

@app.route('/activeLinks', methods=['GET', 'POST'])
def activeLinks():
    if request.method == 'POST':
        file = request.files['pic']
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        textCheck = request.form['enterStoryString']
        brokenLinks = []
        activeLinks = []
        rowCount = 0
        with Display():
            browser = webdriver.Firefox()
            for row in csv_input:
                if rowCount > 0:
                    pageSource = requests.get(row[0], headers={'User-Agent': 'Mozilla/5.0'}).text
                    if textCheck in pageSource:
                        activeLinks.append(row[0])
                    else:
                            browser.get(row[0])
                            time.sleep(5)
                            pageSource = browser.page_source
                            if textCheck in pageSource:
                                activeLinks.append(row[0])
                            else:
                                brokenLinks.append(row[0])
                                print row[0],'no'
                rowCount = rowCount + 1
            browser.quit()
        return render_template("activeLinks.html", data=brokenLinks, dataActive=activeLinks)

