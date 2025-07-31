from django.http.response import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User, auth
from user.models import history, state
import re
from datetime import date
from compress_pickle import load
from operator import itemgetter

def compare_research(a,b):
    if( a["score_research"]  == b["score_research"]):
        return a["H Index"] > b["H Index"]
    return a["score_research"] > b["score_research"]

indexFile = load("./DS/Prof/index_file.lzma")
words = indexFile.keys()
choice = "default"

publications = 5

YEAR = int(date.today().year)

choice_num = 4

def clean_string(text) :
	text = (text.encode('ascii', 'ignore')).decode("utf-8")
	text = re.sub("&.*?;", "", text)
	text = re.sub(">", "", text)
	text = re.sub("[\]\|\[\@\,\$\%\*\&\\\(\)\":]", "", text)
	text = re.sub("-", " ", text)
	text = re.sub("\.+", "", text)
	text = re.sub("^\s+","" ,text)
	text = text.lower()
	return text

def query_result(n, query):

    list_doc = {}

    freq_counter = {}

    if( choice != "Interests"):
        query = list(query.split(" "))
        for q in query:
            q = q.lower()
            curr_done = set()
            if(q == '' or q not in indexFile.keys()):
                continue
            for doc in indexFile[q]:
                if doc['Scholar_ID'] in list_doc:
                    if(doc['Scholar_ID'] not in curr_done):
                        curr_done.add(doc["Scholar_ID"])
                        freq_counter[doc['Scholar_ID']] += 1
                    curr_freq = freq_counter[doc['Scholar_ID']]
                    list_doc[doc['Scholar_ID']]['score'] += 2**curr_freq*doc['score']

                    if(doc['score_name'] != -1):
                        list_doc[doc['Scholar_ID']]['score_name'] += doc['score_name']
                    if(doc['score_univ'] != -1):
                        list_doc[doc['Scholar_ID']]['score_univ'] += doc['score_univ']
                else :
                    freq_counter[doc['Scholar_ID']] = 1
                    scholar_id = doc['Scholar_ID']
                    list_doc[scholar_id] = doc.copy()

    else :
        query = query.lower()
        query = clean_string(query)
        if(query in indexFile.keys()):
            for doc in indexFile[query]:
                scholar_id = doc['Scholar_ID']
                list_doc[scholar_id] = doc.copy()



    list_data=[]

    for data in list_doc:
        list_data.append(list_doc[data])



    count = 1
    res = []

    if (choice == 'prof_name'):
        for data in sorted(list_data, key=lambda k: (k['score_name'],float(k['H Index'])), reverse=True):
            if(data['score_name'] == -1):
                continue
            res.append(data)
            if (count == n) :
                break
            count+=1

    elif (choice == 'university_name'):
        for data in sorted(list_data, key=lambda k: (k['score_univ'],float(k['H Index'])), reverse=True):
            if(data['score_univ'] == -1):
                continue
            res.append(data)
            if (count == n) :
                break
            count+=1

    elif(choice == 'Interests'):

        for data in sorted(list_data, key=lambda k: ((k['score_research']),float(k['H Index'])), reverse=True):
            if(data['score_research'] == -1):
                continue
            res.append(data)
            if (count == n) :
                break
            count+=1

    elif(choice == 'default'):
        for data in sorted(list_data, key=lambda k: (k['score'],float(k['H Index'])), reverse=True):
            res.append(data)
            if (count == n) :
                break
            count+=1

    return res


def home(request):
    return render(request,"index.html")

class publication:
    def __init__(self,content,link,year):
        self.content = content
        self.link = link
        self.year = year

class prof:
    def __init__(self,id,name,imageURL,institute,interests,hIndex,i10Index,publicatio,homepage,homepage_summary,acPublications,allInterest):
        global publications
        self.id = id
        self.name = name
        self.imageURL = imageURL
        self.institute = institute
        self.interests = interests
        self.hIndex = hIndex
        self.i10Index = i10Index
        self.homepage = homepage
        self.allInterest = allInterest
        self.summary = homepage_summary
        if homepage_summary==None:
            self.summary = "Summary Not Available!"
        actual = []
        for i in acPublications:
            if YEAR-int(i[2])<=publications:
                actual.append(publication(i[0],i[1],i[2]))
        self.publications = len(actual)
        self.acPublications = actual


import time
@csrf_exempt
def home_search(request):
    query = request.POST["search"]
    if request.user.is_authenticated:
        all = history.objects.filter(username=request.user.username,history__startswith=query.lower())
        print(len(all))
        if len(all)==0:
            hist = history(username=request.user.username,history=query.lower())
            collaborativeVector = collaborative()
            similarity = similar(collaborativeVector)
            global finalRecommendationVector
            finalRecommendationVector = getTop(similarity,collaborativeVector,5)
            print(finalRecommendationVector)
            hist.save()
    results_required = 96
    x = time.time()
    search_result = query_result(results_required,query)
    array = []
    result_size = len(search_result)
    for i in range(result_size//3+1):
        temp = []
        for j in range(3):
            if(i*3 + j >= result_size):
                break
            if(search_result[i*3+j]["University_name"] == None or search_result[i*3+j]["University_name"] == 'Homepage'):
                search_result[i*3+j]["University_name"] = "NA"
            temp.append(prof(i*3+j,search_result[i*3+j]["Name"], search_result[i*3+j]["img_src"],search_result[i*3+j]["University_name"][:30],", ".join(search_result[i*3+j]["Research_Interests"][:3])[:80],search_result[i*3+j]["H Index"],search_result[i*3+j]["I10 Index"],len(search_result[i*3+j]["Publications"]),search_result[i*3+j]["home_page_url"],search_result[i*3+j]["home_page_summary"],search_result[i*3+j]["Publications"],search_result[i*3+j]["Research_Interests"]))
        array.append(temp)
    l = len(array)
    if(l>8):
        extra1 = array[8:16]
    else:
        extra1 = None
    if(l>16):
        extra2 = array[16:24]
    else:
        extra2 = None
    if l>24:
        extra3 = array[24:]
    else:
        extra3 = None
    noResults = []
    if len(array[0])==0:
        noResults = [1]
    array = array[:8]
    global choice_num
    return render(request, "search.html",{"array":array,"placeholder":query,"noResults":noResults, "choice":choice_num, "publi":publications,"extra1":extra1,"extra2":extra2,"extra3":extra3})

@csrf_exempt
def pref(request):
    global choice
    global choice_num
    if(request.body.decode() == 'prof_name'):
        choice = 'prof_name'
        choice_num = 1
    elif(request.body.decode() == 'Interests'):
        choice = 'Interests'
        choice_num = 2
    elif(request.body.decode() == 'university_name'):
        choice = 'university_name'
        choice_num = 3
    else:
        choice = 'default'
        choice_num = 4
    return JsonResponse({1:"done"})


@csrf_exempt
def publi(request):
    global publications
    if(request.body.decode() == '1'):
        publications = 1
    elif(request.body.decode() == '2'):
        publications = 2
    elif(request.body.decode() == '5'):
        publications = 5
    return JsonResponse({1:"done"})


def register(request):
    return render(request,"register.html")

def reg(request):
    name = request.POST["name"]
    email = request.POST["email"]
    password = request.POST["password"]
    user = User.objects.create_user(username=name,password=password,email=email)
    user.save()
    print(user)
    return redirect("/")

def login(request):
    name = request.POST["name"]
    password = request.POST["password"]
    user = auth.authenticate(username=name,password=password)
    if user is not None:
        auth.login(request,user)
        return redirect("/")
    else:
        return redirect("register")

def logout(request):
    auth.logout(request)
    return redirect("/")

def collaborative():
    allUsers = history.objects.all()
    segregate = {}
    for i in allUsers:
        if i.username in segregate:
            segregate[i.username].append(i.history)
        else:
            segregate[i.username] = [i.history]
    otherUsers = {}
    for i in list(segregate.keys()):
        x = segregate[i]
        quer = []
        for j in x:
            quer.append(j)
        other = {}
        for k in quer:
            for j in k.lower().split(" "):
                if j not in other:
                    other[j]=1
        otherUsers[i] = other
    return otherUsers

def similar(collaborativeVector):
    noOfUsers = len(collaborativeVector)
    users = list(collaborativeVector.keys())
    similarity = {}
    for i in users:
        for j in users:
            if i!=j:
                sim = 0
                for k in collaborativeVector[i]:
                    if k in collaborativeVector[j]:
                        sim+=1
                similarity[(i,j)] = sim
                similarity[(j,i)] = sim
    return similarity

def getTop(similarity,collaborativeVector,maxSim):
    noOfUsers = len(collaborativeVector)
    users = list(collaborativeVector.keys())
    finalRecommend = {}
    for i in users:
        tobeSort = []
        for j in users:
            if i!=j:
                tobeSort.append([i,j,similarity[(i,j)]])
        tobeSort.sort(key = itemgetter(2),reverse=True)
        recommend = []
        for k in tobeSort[:maxSim]:
            recommend.append(k[1])
        finalRecommend[i] = recommend
    return finalRecommend

collaborativeVector = collaborative()
similarity = similar(collaborativeVector)
finalRecommendationVector = getTop(similarity,collaborativeVector,5)

@csrf_exempt
def queries(request):
    if request.user.is_authenticated:
        quer = []
        print(request.body.decode())
        all = []
        if request.user.username in finalRecommendationVector:
            for i in finalRecommendationVector[request.user.username]+[request.user.username]:
                all.extend(history.objects.filter(username=i,history__startswith=request.body.decode().lower()))
            all = list(set(all))
        else:
            all = list(set(history.objects.filter(username=request.user.username,history__startswith=request.body.decode().lower())))
        p = set()
        for i in all:
            if i.history not in p:
                quer.append(i.history)
                p.add(i.history)
        return JsonResponse({'list':quer})
    else:
        return JsonResponse({'list':["Machine Learning"]})



@csrf_exempt
def delHistory(request):
    print(request.body.decode())
    all = history.objects.filter(username=request.user.username)
    for i,obj in enumerate(all):
        obj.id = i+1
    return render(request,"history.html",{"history":all})

@csrf_exempt
def delthis(request):
    delete = request.body.decode()
    history.objects.filter(username=request.user.username,history=delete).delete()
    return JsonResponse({1:"done"})