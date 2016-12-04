from collections import Counter
from flask import Flask, request, render_template, send_from_directory
from StringIO import StringIO
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import psycopg2 as pg2
import seaborn as sns
import random
import json
import warnings
import pickle

with warnings.catch_warnings():
    warnings.filterwarnings("ignore",category=DeprecationWarning)
    import mpld3
    from mpld3 import plugins, fig_to_html
    import igraph

app = Flask(__name__)

# function generate query
# function query
# for all packages query
# plot

# Define some CSS to control our custom labels
css = """
table
{
  border-collapse: collapse;
}
th
{
  color: #ffffff;
  background-color: #000000;
}
td
{
  background-color: #cccccc;
}
table, th, td
{
  font-family:Arial, Helvetica, sans-serif;
  border: 1px solid black;
  text-align: right;
}
"""

def run_sql_query(query):
    if not query:
        return []
    # con = sql.connect(db)
    con = pg2.connect(dbname='packages', user='postgres', host='/tmp')
    c = con.cursor()
    data = c.execute(query)
    result = c.fetchall()
    con.close()
    return result


def define_sql_query(package_list):
    input_list = map(lambda x: "'{}'".format(x), package_list)
    input_list = ', '.join(input_list)
    return "SELECT * FROM daily_file_counts WHERE packages IN ({})".format(input_list)


def get_plot_df(package_list):
    '''
    Return df with packages, date, count columns
    '''
    query = define_sql_query(package_list)
    result = run_sql_query(query)
    df = pd.DataFrame(result)
    df.columns = ['packages', 'date', 'count']
    df['date'] = pd.to_datetime(df['date'])
    df = df[(df['date'].dt.year >= 2003) & (df['date']<'2016-06-01')]

    plot_df = df.set_index('date')
    plot_df = plot_df.groupby('packages').resample('MS').sum().reset_index()
    
    # Rolling average time series grouped by package
    pivoted_df = pd.pivot_table(plot_df, index='date', columns='packages', values='count')
    plot_df = pivoted_df.rolling(window=2).mean().stack().reset_index()
    plot_df.columns = ['date', 'packages', 'count']
    plot_df['count'].fillna(0, inplace=True)

    # Rescale file count to scale 1-100
    oldmin, oldmax = plot_df['count'].min(), plot_df['count'].max()
    newmin, newmax = 0, 100
    oldrange = (oldmax - oldmin)  
    newrange = (newmax - newmin)  
    plot_df['count'] = (((plot_df['count'] - oldmin) * newrange) / oldrange) + newmin

    return plot_df


def plot_packages(df):
    fig, ax = plt.subplots(figsize=(11.5, 7))
    ax.grid(True, alpha=0.3)

    labels = []
    points = []

    for i in range(df.shape[0]):
      label = df.ix[[i], :].T
      label.columns = ['Row {0}'.format(i)]
      # .to_html() is unicode; so make leading 'u' go away with str()
      labels.append(str(label.to_html()))


    for pkg in df['packages'].unique():
        plot_df = df[df['packages'] == pkg]
        # plot_df['count'] = pd.rolling_mean(plot_df['count'], window=5, center=True)
        ax.plot(plot_df['date'], plot_df['count'], label=pkg, ls='solid', marker='.', ms=15,
            mfc='None')

    points = ax.plot(df['date'], df['count'], ls='solid', marker='.', ms=15,
           mfc='None', color='None')
 
    ax.set_xlabel('Month')
    ax.set_ylabel('Usage (scaled to 100)')
    ax.set_title('Python Package Trends', size=20)

    return fig, labels, points 


def recommend_packages(g, input_package, neighbor_order=1, weight_method='co-occurence', show_top_n=10):
    # Search graph vertices for node of interest
    for node in g.vs:
        if node['label'] == input_package:
            root_node = node

    # Find neighbors for root node
    neighbor_ids = g.neighborhood(int(root_node['id']), order=neighbor_order)

    # Weight neighbors depending on method
    if weight_method == 'co-occurence':
        neighbor_weights = []
        for nid in neighbor_ids[1:]:
            edge_weight = g.es[g.get_eid(neighbor_ids[0], nid)]['weight']
            neighbor_weights.append(edge_weight)
        neighbor_weights = zip(neighbor_ids[1:], neighbor_weights)
    if weight_method == 'jaccard':
        pairs = []
        for nid in neighbor_ids[1:]:
            pairs.append((neighbor_ids[0], nid))
        neighbor_weights = g.similarity_jaccard(pairs=pairs)
        neighbor_weights = zip(neighbor_ids[1:], neighbor_weights)
    if weight_method == 'count':
        neighbor_weights = []
        for nid in neighbor_ids[1:]:
            edge_count = g.es[g.get_eid(neighbor_ids[0], nid)]['count']
            neighbor_weights.append(edge_count)
        neighbor_weights = zip(neighbor_ids[1:], neighbor_weights)   

    # Return suggestions
    suggestions = []
    for neighbor_id, weight in sorted(neighbor_weights, key=lambda tup: tup[1], reverse=True):
        name = g.vs[neighbor_id]['label']
        suggestions.append(name)

    print 'Total number of connections: {}'.format(len(suggestions))
    print suggestions[:show_top_n]
    return suggestions[:show_top_n]


# Form page to submit text
@app.route('/')
def submission_page():
    global top_packages
    return render_template('index.html', autocomplete=top_packages)


@app.route('/assets/<path:path>')
def send_js(path):
    return send_from_directory('templates/assets', path)


@app.route('/time_series', methods=['GET'])
def time_series():
    print request.args.getlist('user_input%5B%5D')
    package_list = [pkg.strip() for pkg in request.args.getlist('user_input')]
    df = get_plot_df(package_list)
    fig, labels, points = plot_packages(df)
    tooltip = plugins.PointHTMLTooltip(points[0], labels,
                                     voffset=10, hoffset=10, css=css)
    plugins.connect(fig, tooltip)

    graph_html = mpld3.fig_to_html(fig)
    return render_template('time_series.html', graph_html=graph_html, package_list=package_list)


@app.route('/recommender', methods=['GET'])
def recommender():
    global ig
    user_input = request.args['user_input']
    methods = ['jaccard', 'co-occurence', 'count']
    recommendations = zip(*[recommend_packages(ig, user_input, weight_method=m) for m in methods])
    return render_template('recommender.html', 
        user_input=user_input,
        methods=['Neighbors in Common\n(Jaccard Similarity)', 'Weighted Co-occurence\n(NPMI)', 'Unweighted Co-occurence\n(Count)'],
        package_list=enumerate(recommendations))


if __name__ == '__main__':

    with open('data/top_nodes.json') as json_data:
        top_packages = json_data.read()
        
    with open('data/graph.pkl') as f:
        ig = pickle.load(f)
    
    app.run(host='0.0.0.0', port=8080, debug=True)
