# -*- coding: utf-8 -*-

import itertools
from multiprocessing.dummy import Pool
from random import randint
import re
from time import strftime, sleep
import urllib2
import xml.etree.ElementTree as ET

import networkx as nx
import zen

# Zen docs:      http://www.networkdynamics.org/static/zen/html/api/api.html
# NetworkX docs: https://networkx.github.io/documentation/latest/


#################################
###      RUNTIME OPTIONS      ###
#################################

# Choose how many threads to spawn
THREADS_NUM = 1     # 128 threads for amazon ec2 (don't actually do this)

# Choose how long to sleep between each page retrieval
SLEEP = randint(10, 30)

# Choose whether to output additional Zen GML file alongside NetworkX GEXF file
OUTPUT_ZEN_GML = True

# Choose filepaths (no need to specify file extension for OUTPUT_PATH)
JEL_XML_PATH = "jel_classification.xml"
OUTPUT_PATH = "../graphs/econs6"

# Choose which JEL classification codes to include in search
# CATEGORIES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R'] # noqa
# CATEGORIES = ['C', 'D', 'E', 'F', 'G']
CATEGORIES = ['F']

# Choose whether to capture additonal node/edge data
NODE_DATA = True
EDGE_DATA = True

# Turn on/off debug mode (parses only first 5 pages of each category)
DEBUG = True


################################
###     GLOBAL VARIABLES     ###
################################

# Urllib2 user agent
AGENT = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0'

# Webpage to scrape for papers according to JEL code
DB_ROOT = "http://econpapers.repec.org/"
DB_SEARCH_JEL = "scripts/search.pl?iframes=no;jel="
DB_SEARCH_PG = ";pg="
DB_QUERY = urllib2.quote("* ".join(CATEGORIES) + "*", ":/")
URL = DB_ROOT + DB_SEARCH_JEL + DB_QUERY + DB_SEARCH_PG

# String delimiters for paper metadata
PPS_DELIM = "<li>"
PPS_DELIM_LAST = "</ol>"
PAPER_TITLE_START = ".htm'>"
PAPER_TITLE_END = "</a>"
PAPER_AUTH_START = "<i>"
PAPER_AUTH_END = "</i><br>"
PAPER_JEL_START = "JEL-codes:</b> "
PAPER_JEL_END = "<br>"
PAPER_YEAR_START = "Revised:</b> "
PAPER_YEAR_END = "<b>Added"
PAPER_ALTYEAR_START = "Modified:</b>"
PAPER_ALTYEAR_END = "</small>"

# Timestamp
TIME = "%Y-%m-%d %H:%M:%S"


#################################
###     UTILITY FUNCTIONS     ###
#################################

def jelXMLParser(categories):
    """
    Extract JEL classification info from XML file and output to a dict

    Args:
        categories - list of top-level JEL codes to parse

    Return:
        jel_dict - dict of chosen JEL classification info
    """

    jel = ET.parse(JEL_XML_PATH)
    root = jel.getroot()

    # iterate over xml tags and insert into dict
    jel_dict = {}
    for child in root.iter('classification'):
        m = re.search('([A-Z])(?=[0-9][0-9])', child[0].text)
        if m.group(0) in categories:
            jel_dict[child[0].text] = child[1].text

    return jel_dict


def getPages(url):
    """
    Get number of pages in the database

    Args:
        url - URL string containing relevant JEL code

    Return:
        pgs - integer of number of pages
    """

    try:
        req = urllib2.Request(url)
        req.add_header("User-Agent", AGENT)
        print ">>> %s | Getting pages to parse..." % strftime(TIME)
        f = urllib2.urlopen(req)
        s = f.read()
        f.close()
    except:
        print '>>> %s | !!! ConnectionError, retrying...' % strftime(TIME)
        sleep(5)
        getPages(url)

    pgs = int(re.search('(?<=of )\d+', s.split('<br>Documents')[1]).group(0))
    print ">>> %s | Success! Total pages to parse: %i" % (strftime(TIME), pgs)

    return pgs


def parseDbPageWrapper(pg):
    """
    Wrapper function for parsing a single page of the database

    Args:
        pg - integer value of a database page

    Return:
        None
    """

    try:
        url_full = URL + str(pg)
        parseDbPage(G, url_full)
        sleep(SLEEP)
    except:
        print ">>> %s | !!! ParseError, skipping '%s'" % (strftime(TIME), url_full)


def parseDbPage(G, url):
    """
    Parse and isolate relevant HTML segments containing paper metadata

    Args:
        G - zen.Graph() or networkx.Graph() object
        url - URL string to parse

    Return:
        None
    """

    try:
        print ">>> %s | Opening '%s'" % (strftime(TIME), url)
        req = urllib2.Request(url)
        req.add_header("User-Agent", AGENT)
        f = urllib2.urlopen(req)
        s = f.read()
        f.close()
    except:
        print '>>> %s | !!! ConnectionError, retrying...' % strftime(TIME)
        sleep(2)
        getPages(url)

    main = s.split("<h1 class='colored'>Search Results</h1>")[1]

    # get list of papers
    pps = main.split(PPS_DELIM)[1:]
    pps[-1] = pps[-1].split(PPS_DELIM_LAST)[0]

    # iterate over each paper and append data to nodes and edges
    for pp in pps:

        # extract paper metadata
        # pp_title = pp.split(PAPER_TITLE_START)[1].split(PAPER_TITLE_END)[0]
        # pp_auth = pp.split(PAPER_AUTH_START)[1].split(PAPER_AUTH_END)[0]
        pp_jel = pp.split(PAPER_JEL_START)[1].split(PAPER_JEL_END)[0].strip()
        try:
            pp_year = pp.split(PAPER_YEAR_START)[1].split(PAPER_YEAR_END)[0].strip().split("-")[0]
        except:
            pp_year = pp.split(PAPER_ALTYEAR_START)[1].split(PAPER_ALTYEAR_END)[0].strip().split("-")[0]

        # remove unwanted JEL codes not in selected classification
        codes = pp_jel.split()
        new_codes = []
        for idx in xrange(len(codes)):
            if G.has_node(codes[idx]):
                new_codes.append(codes[idx])

        # add node data
        addNodeData(G, pp_year, new_codes)

        # add edge data
        addEdgeData(G, pp_year, new_codes)


def addNodeData(G, year, codes):
    """
    Add data from a single paper to node attributes

    Args:
        G - nx.Graph() object
        year - single year string
        codes - list of JEL codes

    Return:
        None
    """

    for code in codes:
        G.node[code]["citations"] += 1
        if year in G.node[code]:
            G.node[code][year] += 1
        else:
            G.node[code][year] = 1


def addEdgeData(G, year, codes):
    """
    Add data from a single paper to edges

    Args:
        G - nx.Graph() object
        year - single year string
        codes - list of JEL codes

    Return:
        None
    """

    links = list(itertools.combinations(codes, 2))
    for link in links:

        # if edge already exists
        if G.has_edge(link[0], link[1]):

            # get edge info
            data = G[link[0]][link[1]]
            wg = data["weight"]

            # print "Setting weight: %s %s %i" % (link[0], link[1], wg)

            # set new weight
            G[link[0]][link[1]]["weight"] = wg + 1

            # then, set new edge data
            if EDGE_DATA:
                if year in data:
                    G[link[0]][link[1]][year] += 1
                else:
                    G[link[0]][link[1]][year] = 1

        # if edge does not already exist
        else:

            # print "Adding link: %s %s" % (link[0], link[1])

            if EDGE_DATA:
                G.add_edge(link[0], link[1], weight=1)
                G[link[0]][link[1]][year] = 1
            else:
                G.add_edge(link[0], link[1], weight=1)
        # print G.edge_data(link[0], link[1])


def networkxToZen(G):
    """
    Convert NetworkX graph to Zen graph

    Args:
        G - nx.Graph() object

    Return:
        zen.Graph() object
    """

    G_zen = zen.Graph()
    for node in G.nodes_iter():
        G_zen.add_node(node, data=G.node[node])
    for e1,e2 in G.edges_iter():
        G_zen.add_edge(e1, e2, data=G.edge[e1][e2], weight=G.edge[e1][e2]["weight"])
    zen.io.gml.write(G_zen, "econs5_ALL_zen.gml", write_data=True)

    return G_zen

#################################
###          RUNTIME          ###
#################################

# main sentinel
def main():
    # set workers
    pool = Pool(THREADS_NUM)

    # init JEL dict and empty graph
    print ">>> %s | Initialising nodes..." % strftime(TIME)
    global G
    G = nx.Graph()
    jel = jelXMLParser(CATEGORIES)
    for code in jel:
        G.add_node(code, description=jel[code], citations=0)
    print ">>> %s | Initialisation complete" % strftime(TIME)

    # add nodedata and edgedata to graph
    if DEBUG:
        pages = xrange(1, 6)
        print ">>> %s | DEBUG MODE: Proceeding to parse first 5 pages..." % strftime(TIME)
    else:
        pages = xrange(1, getPages(URL) + 1)
    pool.map(parseDbPageWrapper, pages)
    pool.close()
    pool.join()
    print ">>> %s | Parsing completed!" % strftime(TIME)

    # write to file
    print ">>> %s | Now writing GEXF file at '%s.gexf'" % (strftime(TIME), OUTPUT_PATH)
    nx.write_gexf(G, OUTPUT_PATH + '.gexf')
    if OUTPUT_ZEN_GML:
        G_zen = networkxToZen(G)
        print ">>> %s | Now writing GML file at '%s.gml'" % (strftime(TIME), OUTPUT_PATH)
        zen.io.gml.write(G_zen, OUTPUT_PATH + '.gml', write_data=True, use_zen_data=True)
    print ">>> %s | All done!" % strftime(TIME)

    return


if __name__ == "__main__":
    main()
