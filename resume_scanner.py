#!/usr/bin/env python
# coding: utf-8
from __future__ import division, unicode_literals
import random

import re
import sys
import time  # Used to develop Regular Expressions to identify specifc keywords like Phone No, Email addr etc
# import spacy  # Used to develop a Named Entity Recognition model to idenitfy and display keywords
# Used to remove stopwords from the Resume and Job Desc. files
from nltk.corpus import stopwords
from flask import jsonify
# 2nd Approach to tokenize the Job Description and Resume
from nltk.tokenize import word_tokenize
# 1st Approach to tokenize the Job Description and Resume
from sklearn.feature_extraction.text import CountVectorizer
# Used to get the similarity percentage between job descroption and resume
from sklearn.metrics.pairwise import cosine_similarity
from bs4 import BeautifulSoup  # Converts HTML file to Text file
import pandas as pd  # Used to perform Data manipulation tasks
from selenium.webdriver.common.keys import Keys
import requests
import json
from pandas import json_normalize
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from time import sleep
from selenium import webdriver
from itertools import chain
from affinda import AffindaAPI, TokenCredential

import os
import string
import docx2txt  # Converts Docx file to Text file
import PyPDF2  # Converts PDF file to Text file
import nltk  # Used to perform Text preprocessing tasks


nltk.download('stopwords')
nltk.download('punkt')


# The following libraries/Functions were used to scrape hard skills for a particular and industry from the internet


class ResumeScanner():
    '''
    initialize variables needed by the scan operations
    '''

    def __init__(self, resume_file, resume_extension, jd_file, domain, industry, affinda_token, temp_folder):
        # this dictionary will be populated with data from different scan operations and is returned as the scan result.
        self.init_error = None
        self.resume_scores = {'hard_skills': {}, 'soft_skills': {}, 'sales_index': {}, 'best_practices': {},
                              'similarity_check': {}, 'issues': {}}

        # Init the issue array
        self.resume_scores['issues']['sales_index'] = []
        self.resume_scores['issues']['best_practices'] = []
        

        # initing variables
        self.sI = 0
        self.totalPercentageH = 0
        self.totalPercentageS = 0
        self.ATSp = 0
        self.domain = domain
        self.industry = industry
        self.resume_file = resume_file
        self.jd_file = jd_file
        self.extension = resume_file.filename.split('.')[-1]
        self.resume_extension = resume_extension
        self.affinda_token = affinda_token
        self.temp_folder = temp_folder
        
        # NOTE these are stringified resume and jd files, currently needed in the best_practices keywords extractions
        self.resume = self.stringify_file(resume_file, self.extension, 'resume')
        self.jobDesc = self.stringify_file(jd_file, jd_file.filename.split('.')[-1], 'job description')
        # print(jsonify(self.resume))
        # print(self.jobDesc)

    '''
    takes a file (file-like object), returns it's content as a valid string
    '''

    def stringify_file(self, file, extension, file_type):
        file_str = self.fileConv(file, extension)  # convert different formats to str
        if not file_str:
            # constructos must return none.
            self.init_error = {'success': False, 'msg': f'failed to process the {file_type} file'}

        try:
            file_str = file_str.replace(u'\xa0', u' ')  # proccess the file and replace unwanted chrs
            return file_str
        except Exception as e:
            print('failed to read the resume file', e)
            self.init_error = {'success': False, 'msg': f'failed to read the {file_type} file'}

    # files conversions
    def docuToTxt(self, fileName):
        docFile = docx2txt.process(fileName)
        return docFile

    def pdfToTxt(self, file):
        pdfreader = PyPDF2.PdfFileReader(file)
        # print(pdfreader.numPages)
        pageobj = pdfreader.getPage(0)
        pdfFile = pageobj.extractText()
        return pdfFile

    def HTMLToTxt(self, file):
        htmlFile = BeautifulSoup(file.stream, 'html.parser').get_text()
        return htmlFile

    def fileConv(self, file, extension):
        try:
            file.seek(0)
            if extension == "pdf":
                tempPDF = self.pdfToTxt(file)
                return tempPDF
            elif extension == "docx" or extension == "doc":
                tempDOCX = self.docuToTxt(file)
                return tempDOCX
            elif extension == "html":
                tempHTML = self.HTMLToTxt(file)
                return tempHTML
            elif extension == "txt":
                return file.read().decode('utf-8')

        except Exception as e:
            print('error happened during fileConv', e)
            return False

    '''
    this function is responsible for starting the different scans operations
    returns the populated resumes scores dict
    '''

    def start_scan(self):

        # check if there an error happened during the init first, usually related to files error and the scan
        # shouldn't start.
        if self.init_error is not None:
            return self.init_error
        self.resumeTokenize = self.tokenizeNLTK(self.resume)
        self.jobDescTokenize = self.tokenizeNLTK(self.jobDesc)
        
        softSkillRes, hardSkillsRes = self.affindaSkill(self.resume_file)
        softSkillJobD, hardSkillsJobD = self.affindaSkill(self.jd_file)

        if softSkillRes is False or hardSkillsRes is False or softSkillJobD is False or hardSkillsJobD is False:
            # do not continue
            return {'success': False, 'msg': 'skills extraction internal error, please try again later.'}

        try:
            self.hard_skills_match(hardSkillsJobD, hardSkillsRes)
            # print("\n**Hard skills: ", hardSkillsRes, hardSkillsJobD)
            self.soft_skills_match(softSkillJobD, softSkillRes)
            # print("\n**Soft skills: ", softSkillRes, softSkillJobD)
            self.calculate_skills_gap(hardSkillsJobD, hardSkillsRes, softSkillJobD, softSkillRes)

            self.words_count()
            self.measureable_results()
            self.power_verbs()
            self.cliches_buzzwords()
            self.buzzwords_alternatives()
            self.file_type()
            self.best_practices()
            self.similarity_check_accumlation()

        except Exception as e:
            print('error happened during scan: ', e)
            return {'success': False, 'msg': 'error happened during resume scan, please try again.'}

        # print(json.dumps(self.resume_scores, indent=4))
        return {'success': True, 'results': self.resume_scores}

    def hard_skills_match(self, hardSkillsJobD, hardSkillsRes):

        # IF WEB SCRAPPER FAILS, IT WILL BE CAUGHT AND THIS WILL RETURN NONE
        skills = self.getSkills(self.domain, "hard skills")
        if skills == ['']:
            skills = self.getSkills(self.industry, "hard skills")

        print(f'hard skills returned from the scrapper for {self.domain} : ', skills)

        # hardSJob = hardSkillsJobD
        hardSJob = list(dict.fromkeys(hardSkillsJobD))

        hardSRes = hardSkillsRes

        hardS = self.searchSkills(hardSJob, hardSRes)

        presentH = len(hardS[2])
        # notpresentH= len(hardS[3])
        if presentH == 0:
            self.totalPecentageH = 0
        elif presentH != 0:
            self.totalPercentageH = presentH / len(hardSJob)

        # #### Hard Skills Recommendation using the JD skills + the web scrapped skills
        # hardSkills = [x for x in hardSJob if x not in str(hardS[2])[1:-1]]
        self.resume_scores['hard_skills']["present_skills"] = hardS[2]
        self.resume_scores['hard_skills']["not_present_skills"] = hardS[3]
        self.resume_scores['hard_skills']["recommended_skills"] = skills
        # self.resume_scores['hard_skills']["skills_match"] = self.totalPercentageH
        
        """ If there is anything not presented skills, then not presented skills became the issues to fix """
        self.resume_scores['issues']['hard_skills'] = len(hardS[3])

    def soft_skills_match(self, softSkillJobD, softSkillRes):
        try:
            skills = self.getSkills(self.domain, "soft skills")
            # print("---* Soft Skills: ", skills)
            if skills == ['']:
                skills = self.getSkills(self.industry, "soft skills")

            SoftSJob = softSkillJobD
            # SoftSkills = softSkillJobD
            SoftSRes = softSkillRes

            # #### Soft Skills Search Analysis
            softS = self.searchSkills(SoftSJob, SoftSRes)

            totalSoftSkills = len(SoftSJob)
            presentS = len(softS[2])
            notpresentS = totalSoftSkills - len(softS[3])
            if presentS == 0:
                self.totalPecentageS = 0
            elif presentS != 0:
                self.totalPercentageS = presentS / len(SoftSJob)

            self.resume_scores['soft_skills']["present_skills"] = softS[2]
            self.resume_scores['soft_skills']["not_present_skills"] = softS[3]
            self.resume_scores['soft_skills']["recommended_skills"] = skills
            # self.resume_scores['soft_skills']["skills_match"] = self.totalPercentageS

            """ If there is anything not presented skills, then not presented skills became the issues to fix """
            self.resume_scores['issues']['soft_skills'] = len(softS[3])

            # start = time.time()

            with open('SoftSkills-v2.txt') as x:
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
                            print(nsoftSkills[i])
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

            # #len(nsoftSkills)

            def Convert(a):
                it = iter(a)
                res_dct = dict(zip(it, it))
                return res_dct

            softSkillsDict = Convert(nsoftSkills)

            softSkillsDictMod = {}

            for key, value in softSkillsDict.items():
                if value not in softSkillsDictMod:
                    softSkillsDictMod[value] = [key]
                else:
                    softSkillsDictMod[value].append(key)

            in_depth_rec = {}
            for key, value in softSkillsDictMod.items():
                # print(key, ' : ', value)
                in_depth_rec[key] = value
                # print("\n")
        except Exception as e:
            print('Error in soft skill match: ', e)
        else:
            self.resume_scores['soft_skills']['soft_skills_recomendations_in_depth'] = in_depth_rec

    def searchSoftSkills(self, job, res):
        # stop_words = set(stopwords.words('english'))
        # job = [word for word in job if not word in stopwords.words()]

        cachedStopWords = stopwords.words("english")
        res = ' '.join([word for word in res.split() if word not in cachedStopWords])

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

        matched = set(job).intersection(res)

    def tokenizeCountVectorizer(self, text):
        df = pd.DataFrame(
            {'author': ['resume', 'jobDescription'], 'text': text})
        countVec = CountVectorizer()
        countVec_matrix = countVec.fit_transform(text)
        df_dtm = pd.DataFrame(countVec_matrix.toarray(
        ), index=df['author'].values, columns=countVec.get_feature_names())

        # ### Word Frequency
        # <p>In this step, The dataset was transformed using Transpose function to get the frequency for each word in the resume and job description text.</p>
        df_dtm.T.tail(20)

    def tokenizeNLTK(self, text):
        # Split into words
        tokens = word_tokenize(text)
        # convert to lower case
        tokens = [w.lower() for w in tokens]
        # remove punctuation from each word
        table = str.maketrans('', '', string.punctuation)
        stripped = [w.translate(table) for w in tokens]
        return stripped

    # ### Function to search for Soft/Hard skills & Cliches/BuzzWords
    # <p> The following function follows these steps for Hard/Soft Skills or Cliches/BuzzWords Search:
    #     <ul>1. Takes the Hard/Soft Skills or Cliches/BuzzWords and Resume as Input Parameters.</ul>
    #     <ul>2. Remove stopwords</ul>
    #     <ul>3. Perform comparitive Search Analysis to identify which skills is present and which is not in the resume.</ul>
    #     <ul>4. Return the total number of skills found and not found along with the skills as well after search analysis.</ul>
    # </p>

    def searchSkills(self, job, res):
        stop_words = set(stopwords.words('english'))
        job = [word for word in job if not word in stopwords.words()]
        res = [word for word in res if not word in stopwords.words()]

        # cachedStopWords = stopwords.words("english")
        # res = ' '.join([word for word in res.split() if word not in cachedStopWords])

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

    '''
    temporarily save a file
    IMPORTANT NOTE: I NEVER WANTED TO SAVE FILES LOCALLY EVEN TEMPORARILY,
    BUT AFFINDA API REFUSES TO ACCEPT BYTESIO OR ANY FILE-LIKE OBJECT TO BE PASSED TO IT, JUST THE IO.BUFFERREADER FROM THE OPEN
    BEHIND THE SCENES AFFINDA API USES AZURE HTTPREQUEST TO SEND A MULTIPART FORMDATA TO THEIR SERVER. SO THIS IS WORTH FIXING LATER.
    this step happens in this class not in app.py for example because it happens only because of affinda issue
    '''

    def save_temp(self, file):
        print(file, self.temp_folder)
        temp_path = self.temp_folder
        filename = str(random.randint(0,
                                      99)) + file.filename  # adding random nums to the name to avoid any possible concurrency issues.
        file.seek(0)
        file.save(os.path.join(temp_path, filename))

        return temp_path + '/' + filename

    def affindaSkill(self, arg1):
        try:
            softSkill = []
            hardSkill = []

            token = self.affinda_token
            
            credential = TokenCredential(token=token)
            client = AffindaAPI(credential=credential)
            
            file_temp_path = self.save_temp(arg1)
            
            with open(file_temp_path, "rb") as f:
                resume = client.create_resume(file=f)
            os.remove(file_temp_path)

            print('The Affinda returned resume is', resume.as_dict())

            resResult = resume.as_dict()
            for i in resResult:
                tempDict = resResult[i]
                break
            for j in tempDict:
                if j == 'skills':
                    skills = tempDict[j]
            for i in skills:
                for j in i:
                    # print(j, '->', i[j])
                    if i[j] == 'soft_skill':
                        softSkill.append(i.get('name'))
                    elif i[j] == 'hard_skill':
                        hardSkill.append(i.get('name'))
            # softSkill = ['Creativity', 'Problem Solving']
            # hardSkill = ['Mobile engineering', 'Cloud Computing']
            return softSkill, hardSkill
        except Exception as e:

            print('something happened during affinda', e)
            return False, False

    # Web scrape google
    def getSkills(self, domain, skillType):
        try:

            hit_url = f"https://www.google.com/search?q={domain} {skillType}"

            html_conn = requests.get(hit_url)
            data = BeautifulSoup(html_conn.text, 'html.parser')
            div_data = data.find('div', class_="BNeawe s3v9rd AP7Wnd")
            skills = []
            if div_data:
                ul_data = div_data.find('ul')
                if ul_data:
                    for li in ul_data:
                        skills.append(li.text.replace('.', '').strip())
                        if not skills:
                            skill_linkedin = skillType + ' linkedin'
                            status = self.getSkills(domain, skill_linkedin)
                            # print("----Skills: ", skillType, skills)
                            if skills:
                                # print("****____find Skills -----")
                                return skills
                            else:
                                return None
        except Exception as e:
            print("Error occurred in getskills(): ", e)

    # def getSkills(self, domain, skillType):
    #     options = Options()
    #     options.add_argument('--headless')
    #     # aws ubuntu needs this. so chrome can start up, else chromedriver will throw an error saying that chrome has crashed
    #     options.add_argument('--no-sandbox')
    #     # Last I checked this was necessary.
    #     options.add_argument('--disable-gpu')
    #     # options.add_argument("window-size=1920,1080")
    #     # options.add_argument("start-maximized")
    #     # options.add_argument("enable-automation")
    #     # options.add_argument("--disable-infobars")
    #     # options.add_argument("--disable-dev-shm-usage")
    #     driver = webdriver.Chrome(
    #         ChromeDriverManager().install(), options=options)
    #     # driver = webdriver.Chrome(chrome_options=options)
    #
    #     # if skillType == "hard skills":
    #
    #     driver.get("https://www.google.com/")
    #
    #     # try:
    #     #      NOTE: THIS CODE BLOCK DOESNT WORK FOR ME LOCALLY, NOR ON AWS SO I'LL JUST UNCOMMENT IT OUT
    #     #     # //input[@name="q"]
    #     #     # driver.find_element_by_xpath("//input[@name='q']")tHlp8d
    #     #     # driver.find_element_by_xpath("//button[@id='tHlp8d']")
    #     #     driver.find_element_by_xpath("//*[@title='Search']").send_keys(domain + " hard skills")
    #     #     driver.find_element_by_xpath("//*[@title='Search']").send_keys(Keys.RETURN)
    #
    #     # except Exception:
    #
    #     # on aws i found a popup button for cookies
    #     try:
    #         cookies_accept_btn = driver.find_element_by_xpath(
    #             "//button[@id='L2AGLb']")
    #         cookies_accept_btn.click()
    #     except Exception as e:
    #         print('cookie button not found')  # do nothing
    #
    #     try:
    #         print('The job domain is: ', domain)
    #         search_box = driver.find_element_by_xpath(
    #             "/html/body/div[1]/div[3]/form/div[1]/div[1]/div[1]/div/div[2]/input")
    #         search_box.send_keys(
    #             domain + " hard skills" if skillType == "hard skills" else " soft skills")
    #         search_box.send_keys(Keys.RETURN)
    #
    #     except Exception as e:
    #         print('could not select search box')
    #
    #     sleep(1)
    #
    #     try:
    #         skills = driver.find_element_by_xpath("//*[@class='RqBzHd']/ul")
    #         if skills is None:
    #             print('first search scrapping failed')
    #             skills = driver.find_element_by_xpath(
    #                 '//*[@id="rso"]/div[1]/div/div[1]/div/div[1]/div/div/div/div/div[1]/div/div[2]/ul')
    #
    #         skills = skills.text  # if also none an exception will be thrown
    #
    #     except Exception as e:
    #         print('scrapping attempt failed ', str(e))
    #         # stop and return none, the rest of the workflow can continue working.
    #         return None
    #
    #     skills = skills.replace(".", "").split("\n")
    #
    #     # elif skillType == "soft skills": NOTE this is the exact same code repeated, no need to have it
    #
    #     #     driver.get("https://www.google.com/")
    #
    #     #     try:
    #     #         driver.find_element_by_xpath("//*[@title='Search']").send_keys(domain + " soft skills")
    #     #         driver.find_element_by_xpath("//*[@title='Search']").send_keys(Keys.RETURN)
    #
    #     #     except Exception:
    #     #         driver.find_element_by_xpath("/html/body/div[1]/div[3]/form/div[1]/div[1]/div[1]/div/div[2]/input").send_keys(domain + " soft skills")
    #     #         driver.find_element_by_xpath("/html/body/div[1]/div[3]/form/div[1]/div[1]/div[1]/div/div[2]/input").send_keys(Keys.RETURN)
    #
    #     #     sleep(1)
    #
    #     #     try:
    #     #         skills = driver.find_element_by_xpath("//*[@class='RqBzHd']/ul").text
    #     #     except Exception:
    #     #         skills = driver.find_element_by_xpath('//*[@id="rso"]/div[1]/div/div[1]/div/div[1]/div/div/div/div/div[1]/div/div[2]/ul').text
    #
    #     #     skills = skills.replace(".", "").split("\n")
    #
    #     return skills

    # ### Other Keywords

    # pd.set_option('max_colwidth', 2000)
    # pd.options.display.max_rows = 500

    # nlp = spacy.load('en_core_web_sm')
    # # Read the text file
    # #doc = nlp(open('ml.txt', encoding="utf8").read())
    # doc = nlp(resume)

    # Get the entities, labels and explaination to the labels
    # table = []
    # for ent in doc.ents:
    #     table.append([ent.text,ent.label_,spacy.explain(ent.label_)])

    # Create a dataframe from the list created above
    # df2 = pd.DataFrame(table, columns=['Entity', 'Label','Label_Description']).sort_values(by=['Label'])
    # df2

    # Filter on the label just to compare the results with Stanford NLP NER
    # df2.loc[df2['Label'].isin(['PERSON','ORG','PERCENT','MONEY','LOCATION','GPE','DATE'])]

    # Display the enties and their labels in the actual documents.
    # spacy.displacy.render(doc, style='ent',jupyter=True)

    # # SALES INDEX

    # ### Word Count
    # <p>Length() function was used to get the WordCount for resume and job description text.</p>
    # TODO: data structure for all the next functions

    def words_count(self):

        # print("Total Words for Resume File: ",len(resumeTokenize))
        # print("Total Words for Job Description File: ",len(jobDescTokenize))
        word_list = self.resume.split()
        ResumeLength = len(word_list)
        if ResumeLength < 400:
            msg = f"Your resume is {ResumeLength} words, which is less than the recommended minimum of 400 words."
            
            self.resume_scores['issues']['sales_index'].append("words_count")

        elif ResumeLength > 1000:
            msg = f"Your resume is {ResumeLength} words, which is more than the recommended 1000 words."

            self.resume_scores['issues']['sales_index'].append("words_count")
        else:
            msg = f"Your resume is {ResumeLength} words, which is recommended."
            self.sI += 6.25

        self.resume_scores['sales_index']['words_count'] = msg

    def measureable_results(self):

        tempRes = self.resume.lower()
        MRr = 0
        mrPresent = []
        with open('MR.txt', encoding="utf8") as x:
            MR = [line.strip() for line in x]
        for i in MR:
            # print(i)
            if (i in tempRes):
                mrPresent.append(i)
                MRr += 1

        if MRr >= 5:
            self.resume_scores['sales_index'][
                'measureable_results'] = "There are five or more measurable results in your resume"
            self.sI += 6.25
        elif MRr == 4:
            self.resume_scores['sales_index'][
                'measureable_results'] = "There are four measurable results in your resume"
            self.sI += 5
        elif MRr == 3:
            self.resume_scores['sales_index'][
                'measureable_results'] = "There are three measurable results in your resume"
            self.sI += 3.75
        elif MRr == 2:
            self.resume_scores['sales_index']['measureable_results'] = "There are two measurable results in your resume"
            self.sI += 2.5
        elif MRr == 1:
            self.resume_scores['sales_index']['measureable_results'] = "There is one measurable results in your resume"
            self.sI += 1.25
        else:
            self.resume_scores['sales_index'][
                'measureable_results'] = "No measurable results are present in your resume, We recommend including at least 5 measurable results"
            
            self.resume_scores['issues']['sales_index'].append("measureable_results")

    def power_verbs(self):

        tempRes = self.resume.lower()
        vbr = 0
        vbPresent = []
        with open('verbs.txt') as x:
            verbs = [line.strip() for line in x]
            verbs = list(map(str.lower, verbs))
        for i in verbs:
            if (i in tempRes):
                vbPresent.append(i)
                vbr += 1

        if vbr >= 5:
            print("5 or More Action Verbs/Power Words are present in your CV/Resume", str(vbPresent))
            self.sI += 6.25
        elif vbr == 4:
            print("4 Action Verbs/Power Words are present in your CV/Resume", str(vbPresent))
            self.sI += 5
        elif vbr == 3:
            print("3 Action Verbs/Power Words are present in your CV/Resume", str(vbPresent))
            self.sI += 3.75
        elif vbr == 2:
            print("2 Action Verbs/Power Words are present in your CV/Resume", str(vbPresent))
            self.sI += 2.5
        elif vbr == 1:
            print("1 Action Verbs/Power Word is present in your CV/Resume", str(vbPresent))
            self.sI += 1.25
        else:
            print("No Action Verbs/Power Words are present in your CV/Resume \n\n", str(vbPresent))

            self.resume_scores['issues']['sales_index'].append("power_verbs")

        self.resume_scores['sales_index']['power_verbs'] = vbPresent

    def cliches_buzzwords(self):
        tempRes = self.resume.lower()
        cr = 0
        crPresent = []
        with open('cliches.txt') as x:
            cliches = [line.strip() for line in x]
            cliches = list(map(str.lower, cliches))
        for i in cliches:
            if (i in tempRes):
                crPresent.append(i)
                cr += 1

        if cr == '':
            msg = f"No Cliches/Buzzwords are present in your CV/Resume {cr}"
            self.sI += 6.25
        else:
            msg = f"The following Cliches/Buzzwords are present in your CV/Resume: {crPresent}"
            
            self.resume_scores['issues']['sales_index'].append("cliches_buzzwords")

        self.resume_scores['sales_index']['cliches_buzzwords'] = crPresent

    def buzzwords_alternatives(self):
        with open('recom.txt') as x:
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

        recomDict = self.Convert(nrecom)

        recomDictMod = {}

        for key1, value1 in recomDict.items():
            if value1 not in recomDictMod:
                recomDictMod[value1] = [key1]
            else:
                recomDictMod[value1].append(key1)

        self.resume_scores['sales_index']['buzzwords_alternatives'] = recomDictMod
        # print("The following are the alternatives to most common 14 buzzwords that you can include in your CV:\n")
        # for key1, value1 in recomDictMod.items():
        #     print(key1, ' : ', value1)
        #     print("\n")

    def Convert(self, a):
        it = iter(a)
        res_dct = dict(zip(it, it))
        return res_dct

    # # ATS Best Practices

    # ### Resume  File Type
    # <p>os library was used here to get the identify the path for the resume file and python split() function was used to get the extension or file type</p>

    def file_type(self):
        # name, extension = os.path.splitext(self.resume_path)
        if self.resume_extension == 'docx' or 'doc' or 'pdf' or 'txt':
            # print(f"Your resume is '{extension}', which can be easily scanned by ATS")
            self.ATSp += 2.5

            self.resume_scores['best_practices'][
                'file_type'] = f"Your resume is '{self.resume_extension}', which can be easily scanned by ATS"
        else:
            self.resume_scores['best_practices'][
                'file_type'] = f"Your resume is '{self.resume_extension}', which can not be easily scanned by ATS"
            
            self.resume_scores['issues']['best_practices'].append("file_type")

        if self.extension == 'pdf' or self.extension == 'docx':
            self.resume.replace("\n", "")
            self.resume.replace("\t", " ")
            self.resume.replace("  ", " ")
            self.jobDesc.replace("\n", "")
            self.jobDesc.replace("\t", " ")
            self.jobDesc.replace("  ", " ")

    def best_practices(self):

        line = self.resume
        line = line.lower()
        domain1 = self.domain.lower()

        JT = re.findall("%s" % domain1, line)
        if JT == []:
            # print(f"The job title {self.domain} was not found on your resume. We recommend including your target job title to increase your chances of a match.")
            self.resume_scores['best_practices'][
                'job_title_match'] = f"The job title {self.domain} was not found on your resume. We recommend including your target job title to increase your chances of a match."
            
            self.resume_scores['issues']['best_practices'].append("job_title_match")
        else:
            # print(f"The job title {self.domain} was found on your resume, perfect!")
            self.resume_scores['best_practices'][
                'job_title_match'] = f"The job title {self.domain} was found on your resume, perfect!"
            self.ATSp += 2.5

        # #### Email address
        line = self.resume
        matchEmail = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+|[\w.+-]+©[\w-]+\.[\w.-]+', line)
        if matchEmail == [] or matchEmail == " " or matchEmail == None:
            self.resume_scores['best_practices']['email'] = "Email Address not found"

            self.resume_scores['issues']['best_practices'].append("email")
        else:
            self.ATSp += 2.5
            self.resume_scores['best_practices'][
                'email'] = f"Your email {matchEmail.group(0)} is on your resume, nice work!"

        # #### Phone Number
        matchNo = re.findall(
            '([+]\d{2}[-\.\s]??\d{3}[ ]??[-\.\s]??[ ]??\d{3}[-\.\s]??[ ]??\d{4}|[+]\d{1}[-\.\s]??\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|[-\.\s]??[(]??\d{3}[)]??[-\.\s]??\d{3}[-\.\s]??\d{4}|[+]\d{2}[-\.\s]??\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4}|[+] \d{1} [-] \d{1} \d{1} \d{1} [-] \d{1} \d{1} \d{1} [-] \d{1} \d{1} \d{1} \d{1})',
            line)
        if matchNo != [] or matchNo != " ":
            self.ATSp += 2.5
            self.resume_scores['best_practices'][
                'phone'] = f"Your Phone Number '{matchNo[0:2]}' is on your resume, good job!"
        else:
            self.resume_scores['best_practices']['phone'] = ""

            self.resume_scores['issues']['best_practices'].append("phone")

        # #### Education
        matchEd = []
        Ed2 = re.search(
            '((bachelor|bachelors| bs|B.S.|B.A.|B.SC|B.Sc|BS|MSc|M.Sc|MS|PhD|doctor of philosophy|Major|Minor|University |(.*?) Centre|(.*?) Law School|(.*?) School|Academy|Department|Bachelor|BACHELOR|Master|MASTER|(.*?) College|University of)[\w -]*)',
            line)
        if Ed2 != None:
            Ed2 = Ed2.group(0)
        matchEd.append(Ed2)
        print("Education: ", matchEd)
        if matchEd != '':
            self.ATSp += 2.5
            self.resume_scores['best_practices']['education'] = "Required Education is present"
        else:
            self.resume_scores['best_practices']['education'] = "Education is not present"

            self.resume_scores['issues']['best_practices'].append("education")


        # #### Date Formatting
        matchEDD = re.findall(
            r'((1[0-2])\/(\d{4}))|((0[1-9])\/(\d{4}))|((1[0-2])\/(\d{2}))|((0[1-9])\/(\d{2}))|(([1-9])\/(\d{2}))|(([1-9])\/(\d{4}))|((JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC) ([0-9]{4}))|((January|February|March|April|May|June|July|August|September|October|November|December) ([0-9]{4}))|((JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER) ([0-9]{4}))',
            line)  # M/YYYY
        if matchEDD == [] or matchEDD == " ":
            self.resume_scores['best_practices'][
                'date_format'] = "We could not find a date that matched a recommended format. We recommend using one of the following formats: 'M/YY' or 'MM/YY' or 'M/YYYY' or 'MM/YYYY' or 'Month YYYY'."
            
            self.resume_scores['issues']['best_practices'].append("date_format")

        else:
            self.ATSp += 2.5
            self.resume_scores['best_practices']['date_format'] = "We found the recommended Date Format"

        # #### Experience and Education Sections
        # line1 = self.resume
        # r = re.compile(
        #     r'\bEDUCATION\b | \bEXPERIENCE\b | \bEducation\b | \bExperience\b', flags=re.I | re.X)
        # tt = r.findall(line1)
        # if tt == []:
        #     # print("Not Found")
        #     self.resume_scores['best_practices']['experience'] = "Not Found"
        # else:
        #     # print("We found the Experience and Education sections on your resume, nice work!")
        #     self.resume_scores['best_practices'][
        #         'experience'] = 'We found the Experience and Education sections on your resume, nice work!'
        #     self.ATSp += 2.5

        # #### Section Headings Recommendation

        Found = []
        notFound = []
        self.resume_scores['best_practices']['section_headings'] = {}

        headings = ['education', 'experience', "skills", "personal info", 'summary', 'projects',
                    'languages', 'certificates', 'social networks', 'hobbies', "interests", 'contacts']

        for i in headings:
            if i in self.resumeTokenize:
                Found.append(i)
                # print(i.upper(),"Heading Found")
            else:
                notFound.append(i)
                # print(i.upper(),"Heading Not Found")
        if Found != None:
            # print("The following Section Headings were identified in your CV/Resume: \n", [i.upper() for i in Found])
            self.resume_scores['best_practices']['section_headings']['pop_up'] = 'We found the Experience and Education sections on your resume, nice work!'
            self.resume_scores['best_practices']['section_headings']['present'] = [
                i.upper() for i in Found]
            self.resume_scores['best_practices']['section_headings']['not_present'] = [
                i.upper() for i in notFound]
            # print("\n")
            # print("Please add the following Section Headings that were not identified in your CV/Resume: \n", [i.upper() for i in notFound])
        else :
            self.resume_scores['issues']['best_practices'].append("section_headings")
            
        # #### LinkedIn Profile
        LP = re.findall(
            r'(in/[A-z0-9_-]+\/?)|(http(s)?:\/\/([\w]+\.)?linkedin\.com\/in\/[A-z0-9_-]+\/?)|(linkedin\.com\/in\/[A-z0-9_-]+\/?)',
            line)
        if LP == [] or LP == " ":
            # print("No LinkedIn profile")
            self.resume_scores['best_practices']['linkedin'] = 'No LinkedIn profile'
            self.resume_scores['issues']['best_practices'].append("linkedin")

        else:
            # print("Your LinkedIn profile is present on your resume, now you have a higher chance of hearing back!")
            self.ATSp += 2.5
            self.resume_scores['best_practices'][
                'linkedin'] = 'Your LinkedIn profile is present on your resume, now you have a higher chance of hearing back!'

        ### Organisation Name/URL
        # NOTE this shall be provided by the users later, IN THE NEW FRONTEND
        orgName = "UNIVERSITY OF SHEFFIELD"
        orgURL = "https://www.sheffield.ac.uk/"

        orgName = orgName.lower()
        orgURL = orgURL.lower()
        jobDescTemp = self.jobDesc.lower()

        if (orgName in jobDescTemp and orgURL in jobDescTemp):
            self.resume_scores['best_practices'][
                "Organisations_NameAndWebsite"] = f"Add the organization Name '{orgName}' and URL {orgURL} are present in job description"
            self.ATSp += 2.5
        elif orgName in jobDescTemp:
            self.resume_scores['best_practices'][
                "Organisations_NameAndWebsite"] = f"Add the organization Name '{orgName}' is present in job description"
            self.ATSp += 2.5
        elif orgURL in jobDescTemp:
            self.resume_scores['best_practices'][
                "Organisations_NameAndWebsite"] = f"Add the organization URL '{orgURL}' is present in job description"
            self.ATSp += 2.5
        else:
            self.resume_scores['best_practices'][
                "Organisations_NameAndWebsite"] = f"Add the organisation’s name (the potential employer or advertiser) and the website address (URL) for this job advert."

            self.resume_scores['issues']['best_practices'].append("Organisations_NameAndWebsite")

        # UNKOWN CHARACTERS
        symR = []
        unkR = []

        with open('symbols.txt', encoding="utf8") as x:
            sym = [line.strip() for line in x]
        with open('unk.txt', encoding="utf8") as x:
            unkW = [line.strip() for line in x]

        for i in unkW:
            if i in self.resume:
                unkR.append(i)

        if len(unkR) > 0:
            self.resume_scores['best_practices'][
                'Special_Characters'] = f"Unknown/Unreadable Characters are present in your CV/Resume: " + ''.join(
                u for u in unkR)
            self.resume_scores['issues']['best_practices'].append("Special_Characters")
        else:
            self.ATSp += 2.5
            self.resume_scores['best_practices'][
                'Special_Characters'] = f"There are no unknown/unreadable characters on your resume."

    ### Helper Function to Clean Extracted Skills
    def remBracket(self, skillList):
        temp = []
        for i in skillList:
            split_string = i.split("(", 1)
            if split_string[0][-1] == ' ':
                temp.append(split_string[0][:-1])
            else:
                temp.append(split_string[0])
        return temp

    def calculate_skills_gap(self, hard_skills_jd, hard_skills_cv, soft_skills_jd, soft_skills_cv):
        # Job Description HardSkills Occurrences
        jd_skills_count_dict = self.count_skills_in_text(self.jobDesc.lower(), hard_skills_jd)
        cv_skills_count_dict = self.count_skills_in_text(self.resume.lower(), hard_skills_cv)
        hard_skills_gap = self.count_skills_differences(jd_skills_count_dict, cv_skills_count_dict)

        # now for soft skills
        jd_skills_count_dict = self.count_skills_in_text(self.jobDesc.lower(), soft_skills_jd)
        cv_skills_count_dict = self.count_skills_in_text(self.resume.lower(), soft_skills_cv)
        soft_skills_gap = self.count_skills_differences(jd_skills_count_dict, cv_skills_count_dict)

        self.resume_scores['hard_skills']["skills_gap"] = hard_skills_gap
        self.resume_scores['soft_skills']["skills_gap"] = soft_skills_gap

        print('scores after the gaps are calcualted (hard and soft): ',
              (self.resume_scores['hard_skills']["skills_gap"], self.resume_scores['soft_skills']["skills_gap"]))

    def count_skills_in_text(self, targetFileString, skills):

        skills_gap = {}
        extractedSkills = self.remBracket(skills)
        jobSkillCounter = 0

        for skill_name in extractedSkills:
            skill_name = skill_name.lower()
            jobSkillCounter = targetFileString.count(skill_name)

            if jobSkillCounter > 0:
                skills_gap[skill_name] = jobSkillCounter

        print('skills gap: ', skills_gap)

        return skills_gap

    def count_skills_differences(self, jd_skills_count_dict, cv_skills_count_dict):

        skillGapHardDict = []
        for key in jd_skills_count_dict:
            countt1 = jd_skills_count_dict[key]
            if key in cv_skills_count_dict:
                countt2 = cv_skills_count_dict[key]
            else:
                countt2 = 0
            counter = countt2 - countt1
            skillGapHardDict.append([key, countt2, countt1, counter])

        return skillGapHardDict

    # ## Similarity Check Accumulation

    # #### SALES INDEX = 15%
    # #### HARD SKILLS =30%
    # #### SOFT SKILLS =30%
    # #### ATS BEST PRACTICES =25%

    def similarity_check_accumlation(self):

        salesIndex = self.sI
        hardSkills = self.totalPercentageH * 25
        softSkills = self.totalPercentageS * 25
        ATS = self.ATSp
        SimilarityIndex = salesIndex + hardSkills + softSkills + ATS

        self.resume_scores['similarity_check']['sales_index'] = self.getPerc(salesIndex)
        self.resume_scores['similarity_check']['hard_skills'] = self.getPerc(hardSkills)
        self.resume_scores['similarity_check']['soft_skills'] = self.getPerc(softSkills)
        self.resume_scores['similarity_check']['best_practices'] = self.getPerc(ATS)
        self.resume_scores['similarity_check']['similarity_percentage'] = round(SimilarityIndex, 2)

    def getPerc(self, num):
        return int((num / 25) * 100)
