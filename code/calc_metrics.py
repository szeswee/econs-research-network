# -*- coding: utf-8 -*-

from ast import literal_eval
from collections import Counter
import operator
import re
import xml.etree.ElementTree as ET

import networkx as nx
import zen

# Zen docs:      http://www.networkdynamics.org/static/zen/html/api/api.html
# NetworkX docs: https://networkx.github.io/documentation/latest/


#################################
###     UTILITY FUNCTIONS     ###
#################################

def representsFloat(s):
    """
    Check if imput string represents a float type

    Args:
        s - input string

    Return:
        boolean - True if s can be converted to a float, else False
    """
    try:
        float(s)
        return True
    except ValueError:
        return False


def addWeightUpToYear(G, year, alt=False):
    """
    Obtain cumulative edge weight up to a certain year

    Args:
        G - nx.Graph() object
        year - string representing "up to" year
        alt - recursive mode to save computation time if immediate previous years have been computed

    Return:
        None
    """

    if not alt:
        # add a single data attribute tor all edges
        for e1, e2 in G.edges_iter():
            upto_weight = 0
            for y in G.edge[e1][e2]:
                m = re.search("(?<=weight)\d{4}", y)
                if m and int(m.group(0)) <= int(year):
                    upto_weight += G.edge[e1][e2][y]
            G.edge[e1][e2]["weightUpto" + year] = upto_weight

        # add a single data attribute tor all nodes
        for node in G.nodes_iter():
            upto_weight = 0
            for y in G.node[node]:
                m = re.search("(?<=weight)\d{4}", y)
                if m and int(m.group(0)) <= int(year):
                    upto_weight += G.node[node][y]
            G.node[node]["weightUpto" + year] = upto_weight

    else:

        for e1,e2 in G.edges_iter():
            upto_weight = G.edge[e1][e2]["weightUpto" + str(int(year) - 1)] + G.edge[e1][e2]["weight" + year]
            G.edge[e1][e2]["weightUpto" + year] = upto_weight

        for node in G.nodes_iter():
            upto_weight = G.node[node]["weightUpto" + str(int(year) - 1)] + G.node[node]["weight" + year]
            G.node[node]["weightUpto" + year] = upto_weight

    return



def printEigenCent(G):
    """
    Print top 10 nodes with highest eigenvector centrality

    Args:
        G - nx.Graph() object

    Return:
        None
    """
    eigen = nx.eigenvector_centrality(G)
    sorted_eigen = sorted(eigen.items(), key=operator.itemgetter(1), reverse=True)
    print "Eigenvector Centrality (Overall):"
    for i in range(10):
        print '  %i. %s (%1.10f)' % (i + 1, sorted_eigen[i][0], sorted_eigen[i][1])

    return

def list2csv(a,filename):
    f = open(filename,'w')
    f.write(','.join([str(ai) for ai in a]))
    f.close()

def printPageRankCentUpTo(G, year=None):
    """
    Print top 10 nodes with highest PageRank centrality

    Args:
        G - nx.Graph() object

    Return:
        None
    """
    if year != None:
        addWeightUpToYear(G, year)
        pr = nx.pagerank(G, alpha=0.85, weight="weighUpto" + year)
        sorted_pr = sorted(pr.items(), key=operator.itemgetter(1), reverse=True)
        print "\nPageRank Centrality (%s):" % year
        for i in range(10):
            print '  %i. %s (%1.10f)' % (i + 1, sorted_pr[i][0], sorted_pr[i][1])
    else:
        pr = nx.pagerank(G, alpha=0.85, weight="weight")
        sorted_pr = sorted(pr.items(), key=operator.itemgetter(1), reverse=True)
        print "\nPageRank Centrality (Overall):"
        for i in range(10):
            print '  %i. %s (%1.5f)' % (i + 1, sorted_pr[i][0], sorted_pr[i][1])

    return


def printNormalisedWeight(G, code, year=None, alt=False):
    """
    Print the top 5 edges with the highest normalised edge weight for a given node (JEL code)

    Args:
        G - nx.Graph() object
        code - specific node that you are interested in
        year - string representing "up to" year
        alt - recursive mode to save computation time if immediate previous years have been computed

    Return:
        None
    """

    ed = {}
    if year == None:
        nd = G.neighbors(code)
        for nei in nd:
            if G.edge[code][nei]["weight"] != 0:
                G.edge[code][nei]["normWeight"] = float(G.edge[code][nei]["weight"])/float(min(G.node[code]["citations"],G.node[nei]["citations"]))
            else:
                G.edge[code][nei]["normWeight"] = 0.0
        for nei in G.edge[code]:
            ed[nei] = G.edge[code][nei]["normWeight"]
        sorted_ed = sorted(ed.items(), key=operator.itemgetter(1), reverse=True)
        print "\nNormalised edge weights for node %s (Overall):" % code
        for i in range(5):
            print '  %i. %s (%1.5f)' % (i+1,sorted_ed[i][0],sorted_ed[i][1])
    else:
        addWeightUpToYear(G, year, alt)
        nd = G.neighbors(code)
        for nei in nd:
            if G.edge[code][nei]["weightUpto" + year] != 0:
                G.edge[code][nei]["normWeight" + year] = float(G.edge[code][nei]["weightUpto" + year])/float(min(G.node[code]["weightUpto" + year],G.node[nei]["weightUpto" + year]))
            else:
                G.edge[code][nei]["normWeight" + year] = 0.0
        for nei in G.edge[code]:
            ed[nei] = G.edge[code][nei]["normWeight" + year]
        sorted_ed = sorted(ed.items(), key=operator.itemgetter(1), reverse=True)
        print "\nNormalised edge weights for node %s (%s):" % (code, year)
        for i in range(5):
            print '  %i. %s (%1.5f)' % (i + 1, sorted_ed[i][0], sorted_ed[i][1])

    return sorted_ed


def jelXMLParser(categories):
    """
    Extract JEL classification info from XML file and output to a dict

    Args:
        categories - list of top-level JEL codes to parse

    Return:
        jel_dict - dict of top-level JEL classification and sub-level codes as their values
    """

    jel = ET.parse("jel_classification.xml")
    root = jel.getroot()

    # iterate over xml tags and insert into dict
    jel_dict = {}
    for cat in categories:
        jel_dict[cat] = []
        for child in root.iter('classification'):
            m = re.search('([A-Z])(?=[0-9][0-9])', child[0].text)
            if m.group(0) in cat:
                jel_dict[cat].append(child[0].text)

    return jel_dict


def modularity(G, c):
    """
    Calculate modularity of the graph according to given grouping

    Args:
        G - filled zen.Graph() or zen.DiGraph() object
        c - grouping

    Return:
        Tuple of (Q, Qmax)
    """
    d = dict()
    for k, v in c.iteritems():
        for n in v:
            d[n] = k
    Q, Qmax = 0, 1
    for u in G.nodes_iter():
        for v in G.nodes_iter():
            if d[u] == d[v]:
                Q += (int(G.has_edge(v, u)) - G.degree(u) * G.degree(v) / float(G.size())) / float(G.size())
                Qmax -= (G.degree(u) * G.degree(v) / float(G.size())) / float(G.size())
    return Q, Qmax


######################
###     OUTPUT     ###
######################

# main sentinel
def main():
    # read existing graph
    # Due to an issue with reading Zen GML files, we are using NetworkX GEXF files instead
    G = nx.read_gexf("../graphs/econs5_ALL.gexf")
    categories = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R']

    # get general network statistics
    print "Network Statistics:"
    print "  Nodes: %i" % G.__len__()
    print "  Edges: %i" % G.size()
    print "  Average degree: %1.5f" % (float(sum(G.degree().values())) / G.__len__())
    print "  Average weighted degree: %1.5f" % (float(sum(G.degree(weight="weight").values())) / G.__len__())
    print "  Average clustering coefficient: %1.5f" % nx.average_clustering(G)
    print "  Modularity (Q, Q_max): %1.5f, %1.5f" % modularity(G, jelXMLParser(categories))
    print "  Diameter: %1.5f" % nx.diameter(G)
    print "  Average shortest path length: %1.5f" % nx.average_shortest_path_length(G)

    # Get eigenvector centrality (overall)
    printEigenCent(G)

    # Get pagerank centralities
    printPageRankCentUpTo(G)
    printPageRankCentUpTo(G, "2010")
    # printPageRankCentUpTo(G, "2005")
    # printPageRankCentUpTo(G, "2000")
    # feel free to add more if you want

    # get normalised edge weights
    printNormalisedWeight(G, "G01")
    printNormalisedWeight(G, "G01", "2006")


if __name__ == '__main__':
    main()
