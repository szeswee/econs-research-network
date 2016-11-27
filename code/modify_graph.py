# -*- coding: utf-8 -*-

from ast import literal_eval
from collections import Counter
import re

import matplotlib.pyplot as plt
import networkx as nx
import zen

# Zen docs:      http://www.networkdynamics.org/static/zen/html/api/api.html
# NetworkX docs: https://networkx.github.io/documentation/latest/


#################################
###     UTILITY FUNCTIONS     ###
#################################


# check if string can be converted to int or float
def representsFloat(s):
    try: 
        float(s)
        return True
    except ValueError:
        return False


# remove "Others" nodes
def removeNodeOthersCategory(G):
    for node in G.nodes():
        m = re.search("[C-G][0-9]9", node)
        if m:
            G.remove_node(node)
    return


# add category info
def addNodeCategoryDesc(G):
    category = {
        "A": "General Economics & Teaching",
        "B": "Hostory of Economics & Teaching",
        "C": "Mathematical & Quantitative Methods",
        "D": "Microeconomics",
        "E": "Macroeconomics",
        "F": "International Economics",
        "G": "Financial Economics",
        "H": "Public Economics",
        "I": "Health, Education & Welfare",
        "J": "Labor & Demographic Economics",
        "K": "Law & Economics",
        "L": "Industrial Organisation",
        "M": "Business Administration & Business Economics",
        "N": "Economic History",
        "O": "Economic Development, Technological Change & Growth",
        "P": "Economic Systems",
        "Q": "Agricultural, Natural Resource, Environmental & Ecological Economics",
        "R": "Urban, Rural & Regional Economics"}
    for node in G.nodes_iter():
        for k,v in category.items():
            if k in node:
                G.node[node]["category"] = v
    return


# add missing years
def addMissingYears(G, lowerBound, upperBound):
    years = []
    for i in range(lowerBound, upperBound + 1):
        years.append(str(i))
    for node in G.nodes_iter():
        for year in years:
            if year not in G.node[node]:
                G.node[node][year] = 0
    for e1, e2 in G.edges_iter():
        for year in years:
            if year not in G.edge[e1][e2]:
                G.edge[e1][e2][year] = 0
    return


def removeIncorrectYears(G):
    for node in G.nodes():
        for k in dict(G.node[node]):
            if representsFloat(k):
                m = re.search('((19\d)|(20[01]))\d{1}', k)
                if not m:
                    del G.node[node][k]
    for e1, e2 in G.edges():
        for k in dict(G.edge[e1][e2]):
            if representsFloat(k):
                m = re.search('((19\d)|(20[01]))\d{1}', k)
                if not m:
                    del G.edge[e1][e2][k]
    return


def modifyAttributeKeys(G):
    for node in G.nodes():
        for y in G.node[node]:
            if representsFloat(y):
                G.node[node]["weight" + y] = G.node[node][y]
                del G.node[node][y]
    for e1, e2 in G.edges():
        for y in G.edge[e1][e2]:
            if representsFloat(y):
                G.edge[e1][e2]["weight" + y] = G.edge[e1][e2][y]
                del G.edge[e1][e2][y]

    return


# remove self-loops due to parsing errors
def removeSelfEdge(G):
    for e1, e2 in G.edges():
        if e1 == e2:
            G.remove_edge(e1, e2)

    return


# converts NetworkX GEXF graph to Zen GML graph
def writeToZenGML(G):

    G_zen = zen.Graph()
    for node in G.nodes_iter():
        G_zen.add_node(node, data=G.node[node])
    for e1, e2 in G.edges_iter():
        G_zen.add_edge(e1, e2, data=G.edge[e1][e2], weight=G.edge[e1][e2]["weight"])
    zen.io.gml.write(G_zen, "../graphs/econs5_ALL.gml", write_data=True)

    return




#################################
###          RUNTIME          ###
#################################

# main sentinelk
def main():
    # read existing graph
    G = nx.read_gexf('../graphs/econs5_ALL.gexf')

    # cleaning up of graph/node/edge attributes
    removeSelfEdge(G)
    removeNodeOthersCategory(G)
    removeIncorrectYears(G)
    addNodeCategoryDesc(G)
    modifyAttributeKeys(G)
    addMissingYears(G, 2000, 2016)  # we are only concerned with years 2000 to 2016


    # write to new file
    nx.write_gexf("../graphs/econs5_ALL_modified.gexf")
    writeToZenGML(G)


if __name__ == '__main__':
    main()
