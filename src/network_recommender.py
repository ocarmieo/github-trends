from __future__ import division
from collections import Counter
import numpy as np
import pandas as pd
import networkx as nx
import igraph

def create_counter_from_file(filename, transform_function):
    counter = Counter()
    with open(filename) as f:
        for line in f:
            item, count = line.split('\t')
            counter[transform_function(item)] += int(count)
    return counter


def get_normed_edges(node_counter, edge_counter):
    '''
    INPUT (Counter): counter objects for package count, and package edge counts
    OUTPUT (df): dataframe wtih edge, edge count, and normalized edge count (strength)
    '''
    normed_edge_counter = []
    total_node_count = sum(node_counter.itervalues())
    total_edge_count = sum(edge_counter.itervalues())
    for (x, y), edge_count in edge_counter.most_common():
        # Each edge is a connection between package1 and package2 (both in same file)
        if x in node_counter and y in node_counter:
            x_prob = node_counter[x] / total_node_count
            y_prob = node_counter[y] / total_node_count
            xy_prob = edge_count / total_edge_count
            
            pmi = np.log(xy_prob) - np.log(x_prob) - np.log(y_prob)
            npmi = pmi / -np.log(xy_prob)

            normed_edge_counter.append((x, y, edge_count, npmi))

    normed_edge_df = pd.DataFrame(normed_edge_counter)
    normed_edge_df.columns = ['package1', 'package2', 'count', 'npmi']
    return normed_edge_df


def scale_weights(df_col):
    oldmin, oldmax = df_col.min(), df_col.max()
    newmin, newmax = 0, 10
    oldrange = (oldmax - oldmin)  
    newrange = (newmax - newmin)  
    return (((df_col - oldmin) * newrange) / oldrange) + newmin


def create_G_from_tsv(tsv):
    G = nx.Graph()
    f = open(tsv)
    for line in f.readlines():
        p1, p2, weight = line.strip().split('\t')
        G.add_edge(p1, p2, weight=float(weight))
    return G


def create_G_from_df(df):
    G = nx.Graph()
    for line in df.values:
        p1, p2, count, npmi, npmi_scaled, npmi_decile = line
        G.add_edge(p1, p2, weight=npmi_scaled, decile=npmi_decile, count=count)
    return G


def add_galvanize_to_G(G):
    '''
    Input networkx graph object.
    '''
    # Galvanize data
    gdf = load_gdata('data/galvanize_packages.txt')
    gcounter = Counter(gdf['package'])

    # Captured in GitHub graph?
    nodes = node_counter.keys()
    gdf['captured'] = gdf['package'].map(lambda x: 'Captured' if x in nodes else 'Not captured')
    # Captured        601
    # Not captured     24 (custom written packages)
    # Name: captured, dtype: int64

    # Galvanize set of packages
    gset = set(gdf[gdf['captured'] == 'Captured']['package'].values)
    
    for node_name in G.nodes():
        if node_name in gset:
            G.node[node_name]['galvanize'] = 1
        else:
            G.node[node_name]['galvanize'] = 0
    
    return G


def recommend_packages(g, input_package, neighbor_order, weight_method='co-occurence'):
    # Search graph vertices for node of interest
    for node in g.vs:
        if node['label'] == input_package:
            root_node = node

    # Find neighbors for root node
    neighbor_ids = g.neighborhood(int(root_node['id']), order=neighbor_order)

    # Weight neighbors depending on method
    if weight_method == 'co-occurence':
        neighbor_weights = g.es.select(_between = ([neighbor_ids[0]], neighbor_ids[1:]))['weight']
        neighbor_weights = zip(neighbor_ids[1:], neighbor_weights)
    if weight_method == 'jaccard':
        pairs = []
        for nid in neighbor_ids[1:]:
            pairs.append((neighbor_ids[0], nid))
        neighbor_weights = g.similarity_jaccard(pairs=pairs)
        neighbor_weights = zip(neighbor_ids[1:], neighbor_weights)
    if weight_method == 'count':
        neighbor_weights = g.es.select(_between = ([neighbor_ids[0]], neighbor_ids[1:]))['count']
        neighbor_weights = zip(neighbor_ids[1:], neighbor_weights)        

    # Return suggestions
    suggestions = []
    for neighbor_id, weight in sorted(neighbor_weights, key=lambda tup: tup[1], reverse=True):
        name = g.vs[neighbor_id]['label']
        suggestions.append(name)

    print 'Total number of connections: {}'.format(len(suggestions))
    print suggestions[:10]
    return suggestions


def load_gdata(txt):
    f = open(txt)
    data = []
    for line in f.readlines():
        path, statement = line.split(':')
        if '.' in statement:
            main = statement.split('.')[0].strip()
            # sub = '.'join(statement.split('.')[1:])
        else:
            main = statement.strip()
            # sub = ''
        subject = path.split('/')[0]
        data.append((subject, main))
    f.close()
    df = pd.DataFrame(data)
    df.columns = ['subject', 'package']
    return df



if __name__ == '__main__':
    edge_counter = create_counter_from_file('data/edge_counts', lambda x: tuple(eval(x)))
    node_counter = create_counter_from_file('data/node_counts', lambda x: x.strip('"'))

    # Remove edges with less than 300 occurences
    sub_edge_counter = Counter({k:v for k,v in edge_counter.iteritems() if v > 5})
    # test2 = {k:v for k,v in edge_counter.iteritems() if v > 2}

    normed_edge_df = get_normed_edges(node_counter, sub_edge_counter)

    # Edge weights - normalized pointwise mutual information
    # Rescale NPMI to 1-10
    normed_edge_df['npmi_scaled'] = scale_weights(normed_edge_df['npmi'])
    normed_edge_df['npmi_decile'] = pd.qcut(normed_edge_df['npmi'], q=10, labels=range(1, 11))

    # Create networkx graph
    # 6 columns in df: p1, p2, count, npmi, npmi_scaled, npmi_decile
    G = create_G_from_df(normed_edge_df)

    # # List of nodes (1673)
    # graph_nodes = G.nodes()
    # f = open('graph_nodes.txt', 'w')
    # for line in graph_nodes:
    #     f.write('{}\n'.format(line))
    # f.close()

    G = add_galvanize_to_graph(G):

    nx.write_gml(G, 'data/python_graph.gml')

    ig = igraph.read('data/python_graph.gml')
    ig.write_pickle('data/graph.pkl')

    recommendations = recommend_packages(ig, 'textblob', neighbor_order=1, weight_method='jaccard')