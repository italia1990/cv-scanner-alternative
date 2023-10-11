#!/usr/bin/env python
# coding: utf-8

import os
import string
import docx2txt  # Converts Docx file to Text file
import PyPDF2  # Converts PDF file to Text file
import nltk  # Used to perform Text preprocessing tasks

nltk.download('stopwords')
nltk.download('punkt')
import warnings
import pandas as pd  # Used to perform Data manipulation tasks
from bs4 import BeautifulSoup  # Converts HTML file to Text file

from sklearn.metrics.pairwise import \
    cosine_similarity  # Used to get the similarity percentage between job descroption and resume
from sklearn.feature_extraction.text import CountVectorizer  # 1st Approach to tokenize the Job Description and Resume

from nltk.tokenize import word_tokenize  # 2nd Approach to tokenize the Job Description and Resume
from nltk.corpus import stopwords  # Used to remove stopwords from the Resume and Job Desc. files

import spacy  # Used to develop a Named Entity Recognition model to idenitfy and display keywords

import re  # Used to develop Regular Expressions to identify specifc keywords like Phone No, Email addr etc

# The following libraries/Functions were used to scrape hard skills for a particular and industry from the internet
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from time import sleep
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from pandas import json_normalize
import json
import requests

warnings.filterwarnings('ignore')

# ### Similarity Check


sI = 0
totalPercentageH = 0
totalPercentageS = 0
ATSp = 0


# ### Load the data & Convert to txt
# <p>The following functions converts the resume and job description files of every extension(PDF/Docx/HTML) into Text extension to perform the required tasks</p>


def docuToTxt(fileName):
    docFile = docx2txt.process(fileName)
    return docFile


def pdfToTxt(fileName):
    pdffileobj = open(fileName, 'rb')
    pdfreader = PyPDF2.PdfFileReader(pdffileobj)
    # print(pdfreader.numPages)
    pageobj = pdfreader.getPage(0)
    pdfFile = pageobj.extractText()
    pdffileobj.close()
    return pdfFile


def HTMLToTxt(fileName):
    soup = BeautifulSoup(fileName)
    # print(soup.get_text())
    htmlFile = soup.get_text()
    return htmlFile


def fileConv(fileName):
    name, extension = os.path.splitext(fileName)
    if extension == ".pdf":
        tempPDF = pdfToTxt(fileName)
        return tempPDF
    elif extension == ".docx" or extension == ".doc":
        tempDOCX = docuToTxt(fileName)
        return tempDOCX
    elif extension == ".html":
        tempHTML = HTMLToTxt(fileName)
        return tempHTML


# In[7]:


resume = fileConv(r"../../CV - EMPLOYABILITY TRAINER -SEETEC (1).docx")  # Resume File Path
resume = resume.replace(u'\xa0', u' ')
# resume


# In[8]:


jobDesc = fileConv(r"../../JOB DESCRIPTION - Employability Trainer (1).docx")  # Job Description File Path
jobDesc = jobDesc.replace(u'\xa0', u' ')
# jobDesc


# In[9]:


text = [resume, jobDesc]

# ### Feature/Keyword Extraction
# <p> In this step, The resume and job description text file was tokenized with the use of CountVectorizer and NLTK.
#     All of the keywords from the resume and job descriptions text were extracted and form into a text corpus. Further preprocessing will take place here in following steps:</p>
# <li>
#     <ul>Stop words removal</ul>
#     <ul>Lowercase alphabets</ul>
#     <ul>Punctuation removal</ul>
#     <ul>Split keywords</ul>
#     <ul>Tokenize each keywords using scikit learn CountVectorizer and NLTK</ul>
# </li>
# 

# #### Tokenize using CountVectorizer

# In[10]:


# Use sklearn CountVectorizer for keyword extraction
df = pd.DataFrame({'author': ['resume', 'jobDescription'], 'text': text})
countVec = CountVectorizer()
countVec_matrix = countVec.fit_transform(text)
df_dtm = pd.DataFrame(countVec_matrix.toarray(), index=df['author'].values, columns=countVec.get_feature_names())


# #### Tokenize using NLTK

# In[11]:


def tokenizeNLTK(text):
    # Split into words
    tokens = word_tokenize(text)
    # convert to lower case
    tokens = [w.lower() for w in tokens]
    # remove punctuation from each word
    table = str.maketrans('', '', string.punctuation)
    stripped = [w.translate(table) for w in tokens]
    return stripped


resumeTokenize = tokenizeNLTK(resume)
jobDescTokenize = tokenizeNLTK(jobDesc)

print('Tokenized resume', resumeTokenize)

# In[12]:


print('Tokenized jobDesc', jobDescTokenize)

# ### Word Frequency
# <p>In this step, The dataset was transformed using Transpose function to get the frequency for each word in the resume and job description text.</p>

# In[13]:


df_dtm.T.tail(20)


# ### Function to search for Soft/Hard skills & Cliches/BuzzWords
# <p> The following function follows these steps for Hard/Soft Skills or Cliches/BuzzWords Search:
#     <ul>1. Takes the Hard/Soft Skills or Cliches/BuzzWords and Resume as Input Parameters.</ul> 
#     <ul>2. Remove stopwords</ul>
#     <ul>3. Perform comparitive Search Analysis to identify which skills is present and which is not in the resume.</ul>
#     <ul>4. Return the total number of skills found and not found along with the skills as well after search analysis.</ul>
# </p>

# In[14]:


def searchSkills(job, res):
    stop_words = set(stopwords.words('english'))
    job = [word for word in job if not word in stopwords.words()]
    res = [word for word in res if not word in stopwords.words()]

    foundCount = 0
    notFoundCount = 0
    foundSkill = []
    notFoundSkill = []

    for i in job:
        if i in res:
            foundCount += 1
            foundSkill.append(i)
            # print("Found: ",i)
        else:
            notFoundCount += 1
            notFoundSkill.append(i)
            # print("Not Found: ", i)
    return foundCount, notFoundCount, foundSkill, notFoundSkill


# ### EMSI Skills API
# 1. Pass Job Desc as input parameters
# 2. Extract Skills Job Desc.
# 3. Return Matched Skills

# In[82]:


# In[83]:


auth_endpoint = "https://auth.emsicloud.com/connect/token"  # auth endpoint

client_id = "03wgrw4ywk80oo7i"  # replace 'your_client_id' with your client id from your api invite email
client_secret = "ticaeq9e"  # replace 'your_client_secret' with your client secret from your api invite email
scope = "emsi_open"  # ok to leave as is, this is the scope we will used


import requests



payload = "client_id=" + client_id + "&client_secret=" + client_secret + "&grant_type=client_credentials&scope=" + scope  # set credentials and scope
headers = {'content-type': 'application/x-www-form-urlencoded'}  # headers for the response
access_token = json.loads((requests.request("POST", auth_endpoint, data=payload, headers=headers)).text)[
    'access_token']  # grabs request's text and loads as JSON, then pulls the access token from that


# In[84]:


# jobDesc


# In[85]:


# resume


# In[89]:


# Extract skills from a document
def extract_skills_from_document():
    skills_from_doc_endpoint = "https://emsiservices.com/skills/versions/latest/extract"
    #     text = input("Paste the Text: ")
    body = {"text": "... " + jobDesc + " ...", "confidenceThreshold": 1}

    payload = json.dumps(body)
    #     print(payload)
    #     confidence_interval = str(input(".1 to 1, enter the confidence threshold you're willing to accept: "))
    #     payload = "{ \"text\": \"... " + text + " ...\", \"confidenceThreshold\": " + confidence_interval + " }"

    headers = {
        'authorization': "Bearer " + access_token,
        'content-type': "application/json"
    }

    response = requests.request("POST", skills_from_doc_endpoint, data=payload.encode('utf-8'), headers=headers)
    print(response.json()['data'])
    skills_found_in_document_df = pd.DataFrame(json_normalize(response.json()[
                                                                  'data']));  # Where response is a JSON object drilled down to the level of 'data' key
    #     print(type(skills_found_in_document_df))
    #     print(skills_found_in_document_df)
    return skills_found_in_document_df


# extract_skills_from_document()


# In[26]:


from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from time import sleep
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')  # Last I checked this was necessary.
driver = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=options)


def getSkills(domain, skillType):
    if skillType == "hard skills":

        driver.get("https://www.google.com/")

        try:
            driver.find_element_by_xpath("//*[@title='Search']").send_keys(domain + " hard skills")
            driver.find_element_by_xpath("//*[@title='Search']").send_keys(Keys.RETURN)

        except Exception:
            driver.find_element_by_xpath(
                "/html/body/div[1]/div[3]/form/div[1]/div[1]/div[1]/div/div[2]/input").send_keys(
                domain + " hard skills")
            driver.find_element_by_xpath(
                "/html/body/div[1]/div[3]/form/div[1]/div[1]/div[1]/div/div[2]/input").send_keys(Keys.RETURN)

        sleep(1)

        try:
            skills = driver.find_element_by_xpath("//*[@class='RqBzHd']/ul").text
        except Exception:
            skills = driver.find_element_by_xpath(
                '//*[@id="rso"]/div[1]/div/div[1]/div/div[1]/div/div/div/div/div[1]/div/div[2]/ul').text

        skills = skills.replace(".", "").split("\n")

    elif skillType == "soft skills":

        driver.get("https://www.google.com/")

        try:
            driver.find_element_by_xpath("//*[@title='Search']").send_keys(domain + " soft skills")
            driver.find_element_by_xpath("//*[@title='Search']").send_keys(Keys.RETURN)

        except Exception:
            driver.find_element_by_xpath(
                "/html/body/div[1]/div[3]/form/div[1]/div[1]/div[1]/div/div[2]/input").send_keys(
                domain + " soft skills")
            driver.find_element_by_xpath(
                "/html/body/div[1]/div[3]/form/div[1]/div[1]/div[1]/div/div[2]/input").send_keys(Keys.RETURN)

        sleep(1)

        try:
            skills = driver.find_element_by_xpath("//*[@class='RqBzHd']/ul").text
        except Exception:
            skills = driver.find_element_by_xpath(
                '//*[@id="rso"]/div[1]/div/div[1]/div/div[1]/div/div/div/div/div[1]/div/div[2]/ul').text

        skills = skills.replace(".", "").split("\n")

    return skills


# # Web Scraping
# <p> The following function follows these steps for Scraping Hard Skills from the Web:
#     <ul>1. Takes the Job title or Industry name as Input Parameters.</ul> 
#     <ul>2. Use the webdriver library to start the Search process for Hard skills</ul>
#     <ul>3. Scrape the Hard skills if found on the web.</ul>
#     <ul>4. Return the Hard skills.</ul>
# </p>

# # Hard Skills Match
# 1. Use the WebScraper to search for Hard Skills on the internet.
# 2. Use the EMSI Skills API to extract Hard Skills from the Job Description File.
# 3. Perform Search Analysis to identify and match Hard Skills from Job Description and Resume File.
# 4. Return Seach Analysis Result
# 5. Combine Hard Skills from Job Description and Scraped Result and remove duplicates.
# 5. Recommend the combined Hard Skills.

# #### Hard Skills Scraping

# In[27]:


domain = "Amazon Software Development Engineer"
industry = "Information Technology"
skills = getSkills(domain, "hard skills")
# print(type(skills))
if skills == ['']:
    skills = getSkills(industry, "hard skills")
# skills = skills.split()
# skills = skills[7:]
print(skills)

# #### Hard Skills Job Desc API Extraction

# In[28]:


hardSJob = extract_skills_from_document()
hardSJob = hardSJob[hardSJob["skill.type.name"].str.contains('Hard Skill')]
hardSJob = hardSJob['skill.name'].tolist()
hardSkills = hardSJob + skills
hardSkills = list(dict.fromkeys(hardSkills))
hardSJob

# #### Hard Skills Resume API Extraction

# In[29]:


hardSRes = extract_skills_from_document()
hardSRes = hardSRes[hardSRes["skill.type.name"].str.contains('Hard Skill')]
hardSRes = hardSRes['skill.name'].tolist()
hardSRes

# #### Hard Skills Search Analysis

# In[30]:


# hardSJob = (map(lambda x: x.lower(), hardSJob))
# hardSJob = list(hardSJob)
hardS = searchSkills(hardSJob, hardSRes)

# In[31]:


hardS

# #### Hard Skills Matched Result

# In[32]:


pr = str(hardS[2])[1:-1]
if pr == '':
    print("No Hard Skills are present in your CV/Resume.", pr)
elif pr != '':
    print("The following Hard Skills are present in your CV/Resume: \n", pr)
if str(hardS[3])[1:-1] != '':
    print("\nThe following Hard Skills are not present in your CV/Resume:\n", str(hardS[3])[1:-1])

# In[33]:


presentH = len(hardS[2])
notpresentH = len(hardS[3]) - len(hardS[2])
if presentH == 0:
    totalPecentageH = 0
elif presentH != 0:
    totalPercentageH = presentH / notpresentH
totalPercentageH

# #### Hard Skills Recommendation

# In[34]:


hardSkills = [x for x in hardSkills if x not in str(hardS[2])[1:-1]]
print("The following are some of the Hard Skills that if added in your CV can increase job placement chances:\n\n",
      hardSkills)

# # Soft Skills Match
# 1. Use the WebScraper to search for Soft Skills on the internet.
# 2. Use the EMSI Skills API to extract Soft Skills from the Job Description File.
# 3. Perform Search Analysis to identify and match Soft Skills from Job Description and Resume File.
# 4. Return Seach Analysis Result
# 5. Combine Soft Skills from Job Description and Scraped Result and remove dublicates.
# 5. Recommend the combined Soft Skills.

# #### Soft Skills Scraping

# In[35]:


domain = "Amazon Software Development Engineer"
industry = "Information Technology"
skills = getSkills(domain, "soft skills")
# print(type(skills))
if skills == ['']:
    skills = getSkills(industry, "soft skills")
# skills = skills.split()
# skills = skills[7:]
print(skills)

# #### Soft Skills Job Desc API Extraction

# In[36]:


with open(r'./SoftSkills-v2.txt') as x:
    softSkills = [line.strip() for line in x]
matchedSoftSkills = searchSkills(softSkills, jobDesc)

SoftSJob = extract_skills_from_document()
SoftSJob = SoftSJob[SoftSJob["skill.type.name"].str.contains('Soft Skill')]
SoftSJob = SoftSJob['skill.name'].tolist()

SoftSkills = SoftSJob + skills + matchedSoftSkills[3]
# SoftSkills = SoftSJob + skills
SoftSkills = list(dict.fromkeys(SoftSkills))
SoftSJob

# #### Soft Skills Resume API Extraction

# In[37]:


SoftSRes = extract_skills_from_document()
SoftSRes = SoftSRes[SoftSRes["skill.type.name"].str.contains('Soft Skill')]
SoftSRes = SoftSRes['skill.name'].tolist()
SoftSRes

# #### Soft Skills Search Analysis

# In[38]:


softS = searchSkills(SoftSJob, SoftSRes)

# In[39]:


softS

# #### Soft Skills Matched Result

# In[40]:


pr = str(softS[2])[1:-1]
if pr == '':
    print("No Soft Skills from Job Description are present in your CV/Resume", pr)
elif pr != '':
    print("The following Soft Skills are present in your CV/Resume: \n", pr)
if str(softS[3])[1:-1] != '':
    print("\nThe following Soft Skills are not present in your CV/Resume:\n", str(softS[3])[1:-1])

# In[41]:


presentS = len(softS[2])
notpresentS = len(softS[3]) - len(softS[2])
if presentS == 0:
    totalPecentageS = 0
elif presentS != 0:
    totalPercentageS = presentS / notpresentS
totalPercentageS

# #### Soft Skills Recommendation

# In[42]:


SoftSkills = [x for x in SoftSkills if x not in str(softS[2])[1:-1]]
print("The following are some of the Soft Skills related to ", domain,
      "that if added in your CV can increase job placement chances:\n\n", skills)

# In[43]:


with open(r'./SoftSkills-v2.txt') as x:
    softSkills = [line.strip() for line in x]
nsoftSkills = softSkills.copy()
i = 1
while i < len(nsoftSkills):
    nsoftSkills.insert(i, 'x')
    i += (1 + 1)
for i in range(len(nsoftSkills)):
    # print(i)
    if i <= 20:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "INTEGRITY SKILLS"
    if i > 20 and i <= 40:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "COURTESY SKILLS"
    if i > 40 and i <= 60:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "SOCIAL SKILLS"
    if i > 60 and i <= 80:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "COMMUNICATION SKILLS"
    if i > 80 and i <= 100:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "FLEXIBILITY SKILLS"
    if i > 100 and i <= 120:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "TEAMWORK SKILLS"
    if i > 120 and i <= 140:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "RESPONSIBILITY SKILLS"
    if i > 140 and i <= 160:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "WORK ETHIC SKILLS"
    if i > 160 and i <= 180:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "POSITIVE ATTITUDE SKILLS"
    if i > 180 and i <= 196:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "PROFESSIONALISM SKILLS"
    if i > 196 and i <= 240:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "MOST USED SOFT SKILLS"
    if i > 240 and i <= 270:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "EMPLOYERS’ TOP SOFT SKILLS"
    if i > 270 and i <= 288:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "PROBLEM-SOLVING SKILLS"
    if i > 288 and i <= 304:
        if nsoftSkills[i] == 'x':
            nsoftSkills[i] = "ADAPTABILITY SKILLS"

nsoftSkills.append("ADAPTABILITY SKILLS")


# len(nsoftSkills)


# In[44]:


def Convert(a):
    it = iter(a)
    res_dct = dict(zip(it, it))
    return res_dct


softSkillsDict = Convert(nsoftSkills)

# In[45]:


softSkillsDictMod = {}

for key, value in softSkillsDict.items():
    if value not in softSkillsDictMod:
        softSkillsDictMod[value] = [key]
    else:
        softSkillsDictMod[value].append(key)

print("The following are some of the Soft Skills if present in your CV/Resume can increase job placement chances:\n")
for key, value in softSkillsDictMod.items():
    print(key, ' : ', value)
    print("\n")

# ### Other Keywords

# In[46]:


# pd.set_option('max_colwidth', 2000)
# pd.options.display.max_rows = 500

# nlp = spacy.load('en_core_web_sm')
# # Read the text file
# #doc = nlp(open('ml.txt', encoding="utf8").read())
# doc = nlp(resume)


# In[47]:


# Get the entities, labels and explaination to the labels
# table = []
# for ent in doc.ents:
#     table.append([ent.text,ent.label_,spacy.explain(ent.label_)])


# In[48]:


# Create a dataframe from the list created above
# df2 = pd.DataFrame(table, columns=['Entity', 'Label','Label_Description']).sort_values(by=['Label'])
# df2


# In[49]:


# Filter on the label just to compare the results with Stanford NLP NER
# df2.loc[df2['Label'].isin(['PERSON','ORG','PERCENT','MONEY','LOCATION','GPE','DATE'])]


# In[50]:


# Display the enties and their labels in the actual documents.
# spacy.displacy.render(doc, style='ent',jupyter=True)


# # SALES INDEX

# ### Word Count
# <p>Length() function was used to get the WordCount for resume and job description text.</p> 

# In[51]:


# print("Total Words for Resume File: ",len(resumeTokenize))
# print("Total Words for Job Description File: ",len(jobDescTokenize))
ResumeLength = len(resumeTokenize)
if len(resumeTokenize) < 400:
    print(f"Your resume is {ResumeLength} words, which is less than the recommended minimum of 400 words.")
else:
    print(f"Your resume is {ResumeLength} words, which is recommended.")
    sI += 7

# ### Cliches & Buzzwords

# In[52]:


with open(r'./cliches.txt') as x:
    cliches = [line.strip() for line in x]
cb = searchSkills(cliches, resumeTokenize)

# In[53]:


cpr = str(cb[2])[1:-1]
# print(type(spr))
if cpr == '':
    print("No Cliches/Buzzwords are present in your CV/Resume", cpr)
    sI += 4
else:
    print("The following Cliches/Buzzwords are present in your CV/Resume: \n\n", cpr)

# In[54]:


with open(r'./recom.txt') as x:
    recomm = [line.strip() for line in x]
nrecom = recomm.copy()
i = 1
while i < len(nrecom):
    nrecom.insert(i, 'x')
    i += (1 + 1)
for i in range(len(nrecom)):
    # print(i)
    if i <= 26:
        if nrecom[i] == 'x':
            nrecom[i] = "CREATIVE"
    if i > 26 and i <= 48:
        if nrecom[i] == 'x':
            nrecom[i] = "DRIVEN"
    if i > 48 and i <= 70:
        if nrecom[i] == 'x':
            nrecom[i] = "ENERGETIC"
    if i > 70 and i <= 90:
        if nrecom[i] == 'x':
            nrecom[i] = "EXPERIENCED"
    if i > 90 and i <= 106:
        if nrecom[i] == 'x':
            nrecom[i] = "EXPERT"
    if i > 106 and i <= 114:
        if nrecom[i] == 'x':
            nrecom[i] = "INNOVATIVE"
    if i > 114 and i <= 152:
        if nrecom[i] == 'x':
            nrecom[i] = "LEADER"
    if i > 152 and i <= 192:
        if nrecom[i] == 'x':
            nrecom[i] = "MOTIVATED"
    if i > 192 and i <= 214:
        if nrecom[i] == 'x':
            nrecom[i] = "PASSIONATE"
    if i > 214 and i <= 230:
        if nrecom[i] == 'x':
            nrecom[i] = "SKILLED"
    if i > 230 and i <= 246:
        if nrecom[i] == 'x':
            nrecom[i] = "SPECIALIZED"
    if i > 246 and i <= 268:
        if nrecom[i] == 'x':
            nrecom[i] = "STRATEGIC"
    if i > 268 and i <= 296:
        if nrecom[i] == 'x':
            nrecom[i] = "SUCCESSFUL"
    if i > 296 and i <= 340:
        if nrecom[i] == 'x':
            nrecom[i] = "TRUSTWORTHY"
nrecom.append("TRUSTWORTHY")


# In[55]:


def Convert(a):
    it = iter(a)
    res_dct = dict(zip(it, it))
    return res_dct


recomDict = Convert(nrecom)

# In[56]:


recomDictMod = {}

for key1, value1 in recomDict.items():
    if value1 not in recomDictMod:
        recomDictMod[value1] = [key1]
    else:
        recomDictMod[value1].append(key1)

print("The following are the alternatives to most common 14 buzzwords that you can include in your CV:\n")
for key1, value1 in recomDictMod.items():
    print(key1, ' : ', value1)
    print("\n")

# # ATS Best Practices

# ### Resume  File Type <p>os library was used here to get the identify the path for the resume file and python
# split() function was used to get the extension or file type</p>

# In[57]:


fileN = "CVs-and-Job-Descriptions/Amazon-Software-Engineer-CV.docx"
name, extension = os.path.splitext(fileN)
if extension == '.docx' or '.pdf' or '.html':
    print(f"Your resume is '{extension}', which can be easily scanned by ATS")
    ATSp += 3

# ### Keyword Searching
# <p>For this task, Regex library was used. Custom Regular Expression were developed to identify and return each of the following:
#     <ul>1. Job Title Match</ul>
#     <ul>2. Email Address</ul> 
#     <ul>3. Phone Number</ul>
#     <ul>4. Education</ul>
#     <ul>5. Date Formatting</ul>
#     <ul>6. Experience and Education Sections</ul>
#     <ul>7. Section Headings Recommendation</ul>
#     <ul>8. LinkedIn Profile</ul>
# </p>

# #### Job Title Match

# In[58]:


line = resume
line = line.lower()
domain1 = domain.lower()

JT = re.findall("%s" % domain1, line)
if JT == []:
    print(
        f"The job title {domain} was not found on your resume. We recommend including your target job title to increase your chances of a match.")
else:
    print(f"The job title {domain} was found on your resume, perfect!")
    ATSp += 4

# #### Email address

# In[59]:


line = resume
matchEmail = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+|[\w.+-]+©[\w-]+\.[\w.-]+', line)
if matchEmail == [] or matchEmail == " ":
    print("Email Address not found")
else:
    print(f"Your email {matchEmail.group(0)} is on your resume, nice work!")
    ATSp += 3

# #### Phone Number

# In[60]:


matchNo = re.findall(
    '([+]\d{2}[-\.\s]??\d{3}[ ]??[-\.\s]??[ ]??\d{3}[-\.\s]??[ ]??\d{4}|[+]\d{1}[-\.\s]??\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|[-\.\s]??[(]??\d{3}[)]??[-\.\s]??\d{3}[-\.\s]??\d{4}|[+]\d{2}[-\.\s]??\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})',
    line)
if matchNo != [] or matchNo != " ":
    print(f"Your Phone Number '{matchNo[0:2]}' is on your resume, good job!")
    ATSp += 3

# #### Education

# In[61]:


matchEd = []
Ed1 = re.sub(
    r"[\w\W]* ((Hospital|Major|Minor|University|Centre|Law School|School|Academy|Department|Bachelor|BACHELOR|Master|MASTER|University of|B.A.|B.SC|BSc|BS|MSc|M.Sc|MS|PhD)[\w -]*)[\w\W]*$",
    r"\1", line)
Ed2 = re.search(
    '((Hospital|B.A.|B.SC|BSc|BS|MSc|M.Sc|MS|PhD|Major|Minor|University |(.*?) Centre|(.*?) Law School|(.*?) School|Academy|Department|Bachelor|BACHELOR|Master|MASTER|(.*?) College|University of)[\w -]*)',
    line)
# print(Ed2)
if Ed2 != None:
    Ed2 = Ed2.group(0)
# matchEd.append(Ed1)''
matchEd.append(Ed2)
print("Education: ", matchEd)
if matchEd != '':
    ATSp += 3

# #### Date Formatting

# In[62]:


matchEDD = re.findall(
    r'((1[0-2])\/(\d{4}))|((0[1-9])\/(\d{4}))|((1[0-2])\/(\d{2}))|((0[1-9])\/(\d{2}))|(([1-9])\/(\d{2}))|(([1-9])\/(\d{4}))|([ADFJMNOS]\w* [\d]{4})',
    line)  # M/YYYY
if matchEDD == [] or matchEDD == " ":
    print(
        "We could not find a date that matched a recommended format. We recommend using one of the following formats: 'M/YY' or 'MM/YY' or 'M/YYYY' or 'MM/YYYY' or 'Month YYYY'.")
else:
    print("We found the recommended Date Format")
    ATSp += 3

# #### Experience and Education Sections

# In[63]:


line1 = resume
r = re.compile(r'\bEDUCATION\b | \bEXPERIENCE\b | \bEducation\b | \bExperience\b', flags=re.I | re.X)
tt = r.findall(line1)
if tt == []:
    print("Not Found")
else:
    print("We found the Experience and Education sections on your resume, nice work!")
    ATSp += 3

# #### Section Headings Recommendation

# In[64]:


import string

Found = []
notFound = []

headings = ['education', 'experience', "skills", "personal info", 'summary', 'projects',
            'languages', 'certificates', 'social networks', 'hobbies', "interests", 'contacts']

for i in headings:
    if i in resumeTokenize:
        Found.append(i)
        # print(i.upper(),"Heading Found")
    else:
        notFound.append(i)
        # print(i.upper(),"Heading Not Found")
if Found != None:
    print("The following Section Headings were identified in your CV/Resume: \n", [i.upper() for i in Found])
    print("\n")
    print("Please add the following Section Headings that were not identified in your CV/Resume: \n",
          [i.upper() for i in notFound])

# #### LinkedIn Profile

# In[65]:


LP = re.findall(r'(http(s)?:\/\/([\w]+\.)?linkedin\.com\/in\/[A-z0-9_-]+\/?)|(linkedin\.com\/in\/[A-z0-9_-]+\/?)', line)
if LP == [] or LP == " ":
    print("No LinkedIn profile")
else:
    print("Your LinkedIn profile is present on your resume, now you have a higher chance of hearing back!")
    ATSp += 3

# ## Similarity Check Accumulation

# #### SALES INDEX = 15%
# #### HARD SKILLS =30%
# #### SOFT SKILLS =30%
# #### ATS BEST PRACTICES =25%

# In[66]:


print(sI)
print(totalPercentageH)
print(totalPercentageS)
print(ATSp)

# In[67]:


salesIndex = sI
hardSkills = totalPercentageH * 30
softSkills = totalPercentageS * 30
ATS = ATSp
SimilarityIndex = salesIndex + hardSkills + softSkills + ATS

# In[68]:


print("Sales Index: {:.2f}".format(salesIndex))
print("Hard Skills: {:.2f}".format(hardSkills))
print("Soft Skills: {:.2f}".format(softSkills))
print("ATS Best Practices: {:.2f}".format(ATS))
print("\nSimilarity Percentage: {:.2f}".format(SimilarityIndex))

# In[ ]:
