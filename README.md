# Stacker Images

Stacker Images is a web app to automate editing images

## Features

* Single file or csv image editor outputs:
    * Two images: cropped and blurred background from 800x570 to 4000x2857 pixels (with 1080x770 ratio)
    * Original image dimensions and flags small images
* Single file or folder image uploads to AWS
* Scrapes [thestacker.com](https://www.thestacker.com) articles to create content card previews

## Getting Started

Install dependencies using pip

Create AWS configuration file: ~/.aws/credentials
```
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```
Web app will run on http://localhost:5000/. To start app:

```
$ flask run
```

## Built With

* [Flask](https://palletsprojects.com/p/flask/) - Web application framework
* [Pillow](https://pillow.readthedocs.io/en/stable/) - Python imaging library
* [Boto 3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) - AWS SDK for Python