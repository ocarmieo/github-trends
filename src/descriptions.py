from __future__ import division
from collections import Counter
from pandas.io.json import json_normalize
import json
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD, NMF
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
import lda

def load_json_df(filename):
    '''
    INPUT: json new line delimited file
    OUTPUT: pandas dataframe
    '''
    data = []
    for line in open(filename, 'r'):
        data.append(json.loads(line))
    # Use pandas json_normalize to load json nested dicts
    df = json_normalize(data)
    return df


def describe_nmf_results(document_term_mat, W, H, n_top_words = 15):
    # print("Reconstruction error: %f") %(reconst_mse(document_term_mat, W, H))
    for topic_num, topic in enumerate(H):
        print("Topic %d:" % topic_num)
        print(" ".join([feature_words[i] \
                for i in topic.argsort()[:-n_top_words - 1:-1]]))
    return 




if __name__ == '__main__':
    df = load_json_df('data/docstrings')
    df['docstrings'] = df['docstrings'].map(lambda x: x[0])
    df['docstrings'].map(len).mean()
    df = df[df['docstrings'] != '0']

    df['package'] = df['repo_name'].map(lambda x: x.split('/')[-1])

    # ===== Topic modeling =====
    n_features = 5000
    n_topics = 8

    doc_bodies = df['docstrings']
    
    #vectorizer = CountVectorizer(max_features=n_features)
    vectorizer = TfidfVectorizer(max_features=n_features, stop_words='english')
    document_term_mat = vectorizer.fit_transform(doc_bodies)
    feature_words = vectorizer.get_feature_names()
    
    # NMF
    nmf = NMF(n_components=n_topics)
    W_sklearn = nmf.fit_transform(document_term_mat)
    H_sklearn = nmf.components_
    describe_nmf_results(document_term_mat, W_sklearn, H_sklearn)

    # LDA
    cnt_vectorizer = CountVectorizer(max_features=n_features)
    cv_doc_term_mat = cnt_vectorizer.fit_transform(doc_bodies)
    vocab = cnt_vectorizer.get_feature_names()
    model = lda.LDA(n_topics=5, n_iter=1500, random_state=1)
    model.fit_transform(cv_doc_term_mat)  # model.fit_transform(X) is also available
    topic_word = model.components_  # model.components_ also works
    n_top_words = 7
    for i, topic_dist in enumerate(topic_word):
            topic_words = np.array(vocab)[np.argsort(topic_dist)][:-(n_top_words+1):-1]
            print('Topic {}: {}'.format(i, ' '.join(topic_words)))




