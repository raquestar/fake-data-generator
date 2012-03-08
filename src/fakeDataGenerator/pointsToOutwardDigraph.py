'''
Created on Jan 27, 2012

@author: anorberg

Module to convert a series of points distributed by spiralPointDistribution into a graph inspired by proto-adjacency.
Requires spiralPointDistribution as its source, since it's making assumptions about list ordering.
'''
from __future__ import division
from numpy import array as ndarray
import math
from scipy.spatial import Delaunay
from pygraph.classes.digraph import digraph
import itertools
import yapsy
from yapsy.IPlugin import IPlugin

def euclideanDistance(twople):
    """
    Helper function performing the obvious Euclidean distance calculation between two points in N-dimensional space.
    The two points are presented as a tuple of tuple (or other sequences), where the subsequences are the same length.
    """
    if len(twople) != 2:
        raise ValueError("euclideanDistance must take a 2-item tuple containing numeric sequences of equal length")
    a, b = twople
    if len(a) != len(b):
        raise ValueError("euclideanDistance must take a 2-item tuple containing numeric sequences of equal length")
    
    ssquare = 0.0
    
    for ae, be in zip(a, b):
        diff = ae - be
        ssquare += diff * diff
    
    return math.sqrt(ssquare)

def graphFromTriangulation(triang, nSeeds):
    """
    Generate a PyGraph from a Delaunay triangulation generated from a set of points
    that has a specific ordering property: points are listed in radially outwards order.
    This invariant is guaranteed by spiralPointDistribution, and relied on throughout the
    code. This function probably shouldn't actually be used in other contexts unless
    heavily rewritten.
    
    The generated graph will be acyclic (as long as the points are properly ordered)
    and fully connected (regardless).
    
        triang - scipy.spatial.Delaunay triangulation
        nSeeds - number of points that were considered seed nodes in the point
                 distribution. These will be assigned an in-degree of 0.
    """
    pointTuples = []
    for point in triang.points: #ndarray
        pointTuples.append(tuple(point))
    
    graph = digraph()
    for index, point in enumerate(pointTuples):
        if index < nSeeds:
            node_color = "red"
        else:
            node_color = "black"
        graph.add_node(point, [("color", node_color)])
    
    for plex in triang.vertices:
        for src, dest in itertools.combinations(plex, 2):
            if src == dest: #no self edges
                continue
            elif src > dest: #all edges point down the list
                src, dest = dest, src;
            
            if dest < nSeeds: #seeds can't have incoming edges
                continue
            
            edge = (pointTuples[src], pointTuples[dest])
            
            if not graph.has_edge(edge):
                graph.add_edge(edge, euclideanDistance(edge))
                
    return graph

def graphFromPoints(points, nSeeds):
    """
    Generate a PyGraph from a list of points generated by spiralPointDistribution.
    The requirement for spiralPointDistribution is to keep the invariant that
    points are listed in radially outwards order.
    
        points - list of points in radially outward order
        nSeeds - number of points at the same radius from the center that act
                 as the 0-ary nodes in the graph, and were used as the seeds
                 for the spiralPointDistribution. These must be the first N
                 on the list due to the behavior of spiralPointDistribution
    """
    return graphFromTriangulation(Delaunay(ndarray(points)), nSeeds)

def friendly_rename(graph, name_prefix=""):
    """
    Builds a new weighted digraph, based on the provided weighted digraph (which isn't modified), 
    which discards all names in favor of alphanumeric node identifiers.
    """
    nextLetter = ord('A')
    nextNumber = 1
    identifierMap = {}
    newGraph = digraph()
    
    for node in graph.nodes():
        if not graph.incidents(node):
            identifier = name_prefix + chr(nextLetter)
            nextLetter += 1
        else:
            identifier = "@" + name_prefix + str(nextNumber)
            nextNumber += 1
        newGraph.add_node(identifier, graph.node_attributes(node))
        identifierMap[node] = identifier
    
    for edge in graph.edges():
        weight = graph.edge_weight(edge)
        label = graph.edge_label(edge)
        src = identifierMap[edge[0]]
        dest = identifierMap[edge[1]]
        new_edge = (src, dest)
        attrs = graph.edge_attributes(edge)
        newGraph.add_edge(new_edge, weight, label, attrs)
        
    return newGraph

class IPruneEdges(IPlugin):
    """
    Yapsy plugin interface for algorithms that prune edges off the graph of the Delaunay triangulation. 
    """
    def prune(self, graph):
        """
        Given a graph, remove some of its edges to make it shaped more like an interaction network.
        Return the pruned graph, but this is expected to modify the original (and that is what should be returned).
        """
        raise NotImplemented("IPruneEdges is a plugin interface. prune MUST be overridden!")
    

def prunerImplementations(paths):
    """
    Return an iterable of plugin-info for every locatable implementation of this interface.
    """
    manager = yapsy.PluginManager()
    manager.setPluginPlaces(paths)
    from fakeDataGenerator.pointsToOutwardDigraph import IPruneEdges as foreignPruneEdges
    manager.setCategoriesFilter({
        "PruneEdges" : foreignPruneEdges,                         
        })
    manager.collectPlugins()
    return manager.getPluginsOfCategory("PruneEdges"), manager