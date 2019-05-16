"""Word Cloud v1"""

import sys
sys.path.append('tools')

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
from pymongo import MongoClient
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator


def get_col2(conn_detail: list):
    uri, db, collection = conn_detail
    return MongoClient(uri)[db][collection]


def plot(thing_to_plot):
    plt.imshow(thing_to_plot)
    plt.axis("off")
    plt.show()
    return


if __name__ == '__main__':
    col1 = ['DB_URI', 'JL_Scraping', 'DS_RawData']
    col2 = ['DB_URI', 'JL_Scraping', 'DS_CompLoc']
    
    with get_col2(col1).find({}) as d1, get_col2(col2).find({}) as d2:
        descrip_concat = ' '.join(row['Description'].strip().replace('\t', ' ').replace('\n', ' ') 
                                  for row in d1 if 'Description' in row)
        pass
    
    more_stpwrds = ['years', 'experience', 'sexual', 'sex', 'gender', 'race', 'religion', 'York', 
                    'United', 'States', 'Description', 'color', 'candidate', 'employer', 'job', 
                    'without', 'regard', 'must', 'able', 'national', 'origin', 'veteran', 
                    'applicant', 'work', 'will', 'education']
    
    for stpwrd in more_stpwrds:
        STOPWORDS.add(stpwrd)
    
    print('plotting...')
    plot(WordCloud(relative_scaling=1.0, 
                   stopwords=STOPWORDS, 
                   # background_color='white', 
                   width=1600, 
                   height=900).generate(descrip_concat))


