# Multi User Blog - 01/8/2017

## Introduction
A basic blog that supports multiple users and allows users to create posts, 
comment on posts, and like posts.

## Instalation
Make sure you have `Python`, `Google Cloud SDK` installed, and a Google API 
called `Google App Engine`. You will need to make an account for the latter.

Go to https://console.developers.google.com/appengine and create an account. 
Once everything is completed, download and install `Google App Engine SDK for 
Python`.

Open the `Google Cloud SDK Shell`, login to the gcloud, and accept.
```
> gcloud auth login
```

## How To Deploy
Create new project in the Google API. Open the `Google Cloud SDK Shell`. 
Set the project you wish to work with. Change path to your project's directory 
and deploy your app. You can view the website by using the browse command, or 
entering the deployed url into your web browser.
```
> gcloud projects list
> gcloud config set project [PROJECT_ID]

> cd [THE\PATH\OF\YOUR\PROJECTproject]
> gcloud app deploy app.yaml index.yaml

> gclowd app browse
```
To view the name of your current project type in:
```
> gcloud info |tr -d '[]' | awk '/project:/ {print $2}'
[PROJECT_ID]
> 
```
Deploying url: [https://[PROJECT_ID].appspot.com](
https://multi-user-blog-181011.appspot.com/)

### Alternetive Browsing
Open the `Google App Engine Launcher`, click on `File` -> 
`Add Existing Application`, browse or enter the correct path and click `Add`. 
Click on the big button called `Run`, and then on the button called `Browse`.

Please note that this will only work if the app.yaml has both the `'version'` 
and `'application'` fields specified.
