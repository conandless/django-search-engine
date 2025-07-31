import re
import json
from compress_pickle import dump
import math


# Clean string function
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

def indexing():
	max_h_index = 0 
	df_data={}
	df_data_name = {}
	df_data_univ = {}
	df_data_research = {}
	tf_data={}
	tf_data_research={}
	tf_data_name={}
	tf_data_univ={}
	idf_data={}
	idf_data_name={}
	idf_data_research={}
	idf_data_univ={}
	tf_idf = {}
	output_file_name = "index_file.lzma"
	input_file_name = "prof.json"

	prof_data_list = open(input_file_name, encoding="utf8").read().split("\n")
	stopwords = open("./stopword.txt").read().split("\n")

	prof_data = []
	for row in prof_data_list:
		try:
			prof_data.append(json.loads(row))
		except:
			continue

	for row in prof_data:
		if row["H Index"] == None:
			row["H Index"] = 0
		max_h_index = max(max_h_index, int(row["H Index"]))
		tf={} 
		tf_name={}
		tf_univ={}
		tf_research={}
		#clean and list word
		for data in row['Name'].split():
			clean_name = clean_string(data)
			if clean_name in stopwords:
				continue
			if clean_name in tf :
				tf[clean_name] += 3
			else :
				tf[clean_name] = 13

			#df whole document frequency
			if clean_name in df_data :
				df_data[clean_name] += 1
			else :
				df_data[clean_name] = 1

			# Name Score 
			if clean_name in tf_name :
				tf_name[clean_name] += 1
			else :
				tf_name[clean_name] = 1

			#df whole document frequency
			if clean_name in df_data_name :
				df_data_name[clean_name] += 1
			else :
				df_data_name[clean_name] = 1
				
		univ_name  = row['University_name']
		if(univ_name == None):
			univ_name = ""
		for data in univ_name.split():
			if(data == ''):
				continue
			univ_name = clean_string(data)
			if univ_name in stopwords:
				continue
			if univ_name in tf :
				tf[univ_name] += 3
			else :
				tf[univ_name] = 13

			#df whole document frequency
			if univ_name in df_data :
				df_data[univ_name] += 1
			else :
				df_data[univ_name] = 1

			# University Score
			if univ_name in tf_univ :
				tf_univ[univ_name] += 1
			else :
				tf_univ[univ_name] = 1

			#df whole document frequency
			if univ_name in df_data_univ :
				df_data_univ[univ_name] += 1
			else :
				df_data_univ[univ_name] = 1

		for data in row['Publications']:
			clean_publications = clean_string(data[0])
			list_word = clean_publications.split(" ")		
			for word in list_word :
				if word in stopwords:
					continue
				#tf row frequency
				if word in tf :
					tf[word] += 1
				else :
					tf[word] = 1

				#df whole document frequency
				if word in df_data :
					df_data[word] += 1
				else :
					df_data[word] = 1

		for data in row['Research_Interests']:
			clean_interests = clean_string(data)
			list_word = clean_interests.split(" ")
			for word in list_word:
				if word in tf:
					tf[word] += 2
				else:
					tf[word] = 3
				# can also add weightage to the interest 
				if word in df_data :
					df_data[word] += 1
				else :
					df_data[word] = 1

			
			# Research Interest Score
			if clean_interests in tf:
				tf[clean_interests] += 1
			else:
				tf[clean_interests] = 1
			# can also add weightage to the interest 
			if clean_interests in df_data :
				df_data[clean_interests] += 1
			else :
				df_data[clean_interests] = 1

			if clean_interests in tf_research:
				tf_research[clean_interests] += 1
			else:
				tf_research[clean_interests] = 1
			# can also add weightage to the interest 
			if clean_interests in df_data_research :
				df_data_research[clean_interests] += 1
			else :
				df_data_research[clean_interests] = 1

		tf_data[row['Scholar_ID']] = tf.copy()
		tf_data_research[row['Scholar_ID']] = tf_research.copy()
		tf_data_univ[row['Scholar_ID']] = tf_univ.copy()
		tf_data_name[row['Scholar_ID']] = tf_name.copy()

	# Calculate Idf
	for row in df_data :
		idf_data[row] = 1 + math.log10(len(tf_data)/df_data[row])

	for row in df_data_name :
		idf_data_name[row] = 1 + math.log10(len(tf_data_name)/df_data_name[row])
	
	for row in df_data_research :
		idf_data_research[row] = 1 + math.log10(len(tf_data_research)/df_data_research[row])
	
	for row in df_data_univ :
		idf_data_univ[row] = 1 + math.log10(len(tf_data_univ)/df_data_univ[row])

	for word in df_data:
		list_doc = []
		scholar_Id_list = set()
		for data in prof_data:
			if(data['Scholar_ID'] in scholar_Id_list):
				continue
			scholar_Id_list.add(data['Scholar_ID'])
			tf_value = 0
			tf_name_value = 0
			tf_research_value = 0
			tf_univ_value = 0
			
			weight_name = -1
			weight_research = -1
			weight_univ = -1

			if word in tf_data[data['Scholar_ID']] :
				tf_value = tf_data[data['Scholar_ID']][word]

			if word in tf_data_name[data['Scholar_ID']] :
				tf_name_value = tf_data_name[data['Scholar_ID']][word]
				weight_name = (tf_name_value*idf_data_name[word])
			
			if word in tf_data_research[data['Scholar_ID']] :
				tf_research_value = tf_data_research[data['Scholar_ID']][word]
				weight_research = (tf_research_value*idf_data_research[word])
			
			if word in tf_data_univ[data['Scholar_ID']] :
				tf_univ_value = tf_data_univ[data['Scholar_ID']][word]
				weight_univ = (tf_univ_value*idf_data_univ[word])
			
			weight = (tf_value*idf_data[word])

			doc = {
				'Scholar_ID' : data['Scholar_ID'],
				'Name' : data['Name'],
				'img_src' : data['img_src'],
				'H Index' : data['H Index'],
				'Citations' : data['Citations'],
				'I10 Index' : data['I10 Index'],
				'Publications' : data['Publications'],
				'home_page_url' : data['home_page_url'],
				'Research_Interests' : data['Research_Interests'],
				'University_name' : data['University_name'],
				'home_page_summary' : data['home_page_summary'],
				'score' : weight,
				'score_name': weight_name,
				'score_research':weight_research,
				'score_univ': weight_univ
			}
			if doc['score'] != 0 :
				list_doc.append(doc)	
			
		tf_idf[word] = list_doc.copy()

	with open(output_file_name, 'wb') as file:
		dump(tf_idf,file , compression="lzma", set_default_extension=False)
	

if(__name__ == '__main__'):
	indexing()